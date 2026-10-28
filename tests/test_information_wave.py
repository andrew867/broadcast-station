import time
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from skycam.travel import parse
from skycam.space_weather import parse as parse_space
from skycam.scene_policy import ScenePolicy
from skycam.rundown import Cue,Rundown,RundownConfig
from skycam.program_clock import ProgramClock,ClockConfig,ClockRule


class Provider:
    def __init__(self,value):self.value=value
    def public(self,*args,**kwargs):return self.value


def test_travel_parser_keeps_exceptions_and_drops_normal_rows():
    now=1_800_000_000
    result=parse({
      'roads':[{'RoadwayName':'HWY-1','LocationDescription':'East of town','Primary Condition':'Snow covered','Visibility':'Poor','LastUpdated':now},
               {'RoadwayName':'HWY-2','Primary Condition':'Bare and dry'}],
      'events':[{'RoadwayName':'HWY-1','Description':'All lanes closed','EventType':'closures','Severity':'Major','IsFullClosure':True,'LastUpdated':now}],
      'ferries':[{'ServiceName':'Island service','Status':'Out of Service','Details':'Weather','LastUpdated':now},
                 {'ServiceName':'Other','Status':'In Service On Schedule'}],
      'winds':[{'RoadwayName':'HWY-1','Location':'Wreckhouse','Advisory':'High wind warning','Description':'Use caution','LastUpdated':now},
               {'Advisory':'No wind advisory'}],
      'advisories':[{'Message':'Travel delayed','HighImportance':True,'LastUpdated':now}],
    },now)
    assert len(result['roads'])==1 and result['roads'][0]['condition']=='Snow covered'
    assert result['events'][0]['closure'] is True
    assert len(result['ferries'])==1 and len(result['winds'])==1 and result['advisories'][0]['important']


def test_space_weather_parser_uses_sub_auroral_row():
    html='''<p>2026-10-28 Day of year 301 issued at 11:17 UT</p>
      <table><tr><th></th><th>Sub-Auroral</th><th>Auroral</th><th>Polar</th></tr>
      <tr><td>Current Conditions</td><td>quiet</td><td>unsettled</td><td>unsettled</td></tr>
      <tr><td>24 Hour Forecast</td><td>quiet unsettled intervals</td><td>active</td><td>quiet</td></tr></table>'''
    data=parse_space(html)
    assert data['current']['sub_auroral']=='quiet'
    assert data['forecast_24h']['auroral']=='active'
    assert data['issued']=='2026-10-28 11:17 UTC'


def test_scene_policy_conditions_do_not_block_manual_availability():
    policy=ScenePolicy(weather=Provider({'forecast_available':False,'fetched_at':1}),
                       travel=Provider({'available':True,'exceptional':True,'summary':'One closure','checked_at':2}))
    assert policy.cue_eligible('weather-timeline','auto') is False
    assert policy.cue_eligible('weather-timeline','always') is True
    assert policy.cue_eligible('nl-travel','when-exception') is True
    assert policy.clock_eligible('travel-exceptions') is True
    assert Cue(camera='weather-timeline').condition=='auto'


def test_scene_confidence_current_weather_and_unavailable_calendar():
    policy=ScenePolicy(weather=Provider({'forecast_available':True,'fetched_at':3}),notices=None)
    assert policy.scene('weather-timeline')['state']=='current'
    assert policy.scene('community-calendar')['state']=='unavailable'


def test_future_approved_calendar_item_is_current():
    now=datetime(2026,10,28,12,tzinfo=timezone.utc)
    item={'approved':True,'starts_at':(now+timedelta(days=2)).isoformat(),'ends_at':(now+timedelta(days=2,hours=2)).isoformat()}
    policy=ScenePolicy(notices=Provider({'items':[item]}))
    result=policy.scene('community-calendar',now.timestamp())
    assert result['current'] and result['detail']=='1 approved upcoming item'


def test_briefing_plays_when_any_composite_source_is_current():
    policy=ScenePolicy(weather=Provider({'forecast_available':False}),travel=Provider({'available':True,'checked_at':2}),outages=Provider({'fresh':False}))
    assert policy.scene('morning-briefing')['current']
    assert policy.scene('morning-briefing')['detail']=='1 of 3 briefing sources current'


def test_conditional_cue_skips_automatically_but_remains_a_valid_manual_scene(tmp_path):
    calls=[];rundown=Rundown(tmp_path,lambda *args:calls.append(args))
    rundown.condition_eligible=lambda scene,condition:scene!='nl-travel'
    rundown.save(RundownConfig(cues=[Cue(camera='nl-travel'),Cue(camera='map')]))
    rundown.action('start')
    assert calls[-1][0]=='map'
    assert Cue(camera='nl-travel',condition='always').camera=='nl-travel'



class Confidence:
    def __init__(self,rows):self.rows=rows
    def confidence(self):return {'sources':self.rows}
    def public(self):return {'timelapse':{}}


def test_camera_policy_holds_recent_picture_then_skips_stale_single_camera(monkeypatch):
    from skycam.sources import CAMERAS
    now=time.time();monkeypatch.setitem(CAMERAS['cam1'],'enabled',True);monkeypatch.setitem(CAMERAS['cam2'],'enabled',True)
    policy=ScenePolicy(features=Confidence([
        {'id':'cam1','fresh':False,'at':now-90},
        {'id':'cam2','fresh':False,'at':now-240},
    ]))
    assert policy.scene('cam1',now)['state']=='cached'
    assert policy.cue_eligible('cam1','auto') is True
    assert policy.scene('cam2',now)['state']=='unavailable'
    assert policy.cue_eligible('cam2','auto') is False
    assert policy.cue_eligible('cam2','always') is True


def test_quad_remains_eligible_when_one_member_has_a_recent_picture(monkeypatch):
    from skycam.sources import CAMERAS,QUADS
    now=time.time()
    for camera in QUADS['quad']:monkeypatch.setitem(CAMERAS[camera],'enabled',True)
    policy=ScenePolicy(features=Confidence([{'id':QUADS['quad'][0],'fresh':True,'at':now}]))
    result=policy.scene('quad',now)
    assert result['state']=='current' and policy.cue_eligible('quad','auto') is True

def test_program_clock_local_hour_filter(tmp_path):
    zone=ZoneInfo('America/St_Johns');playlist='a'*32
    resolve=lambda _:{'name':'Morning','config':{'cues':[{'camera':'map'}]}}
    before=datetime(2026,10,28,11,59,tzinfo=zone).timestamp()
    clock=ProgramClock(tmp_path,resolve,now=before)
    clock.config=ClockConfig(enabled=True,rules=[ClockRule(id='morning',playlist_id=playlist,every_minutes=60,hours=[12])])
    assert datetime.fromtimestamp(clock.upcoming(before)['at'],zone).hour==12
    with pytest.raises(ValueError):ClockRule(id='bad',playlist_id=playlist,hours=[12,12])


def director_request(address,key=None):
    headers=[] if key is None else [(b'x-director-key',key.encode())]
    return Request({'type':'http','method':'GET','path':'/api/director/status','headers':headers,'client':(address,1234),'server':('station',8765),'scheme':'http','query_string':b''})


def test_director_requires_private_address_and_exact_key(monkeypatch):
    from skycam import app as module
    fixture_value='x'*24
    monkeypatch.setattr(module,'director_key',fixture_value)
    module.require_director(director_request('127.0.0.1',fixture_value))
    with pytest.raises(HTTPException) as missing:module.require_director(director_request('127.0.0.1'))
    assert missing.value.status_code==401
    with pytest.raises(HTTPException) as public:module.require_director(director_request('8.8.8.8',fixture_value))
    assert public.value.status_code==403
