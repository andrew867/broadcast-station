from datetime import datetime,timedelta,timezone,date
from zoneinfo import ZoneInfo
import pytest
from PIL import Image
from skycam.map_theme import MapTheme,MapThemeRequest,solar_events,TIMEZONE
from skycam.map_renderer import night_basemap,MapRenderer

def test_auto_changes_at_local_sunrise_and_sunset(tmp_path):
    theme=MapTheme(tmp_path)
    rise,setting=solar_events(date(2026,10,16))
    assert theme.public(rise-timedelta(microseconds=1))['effective']=='night'
    assert theme.public(rise)['effective']=='day'
    assert theme.public(setting-timedelta(microseconds=1))['effective']=='day'
    after=theme.public(setting)
    assert after['effective']=='night'
    assert datetime.fromisoformat(after['next_change_at']).date()==date(2026,10,17)

def test_manual_choice_persists_and_overrides_sun(tmp_path):
    theme=MapTheme(tmp_path)
    for mode,hour in [('day',0),('night',12)]:
        theme.save(MapThemeRequest(mode=mode))
        restored=MapTheme(tmp_path)
        state=restored.public(datetime(2026,10,16,hour,tzinfo=ZoneInfo(TIMEZONE)))
        assert state['mode']==mode and state['effective']==mode
        assert state['next_change_at'] is None
    with pytest.raises(ValueError):MapThemeRequest(mode='twilight')

def test_midnight_and_dst_use_newfoundland_date(tmp_path):
    theme=MapTheme(tmp_path)
    # UTC has reached the next day, Newfoundland has not.
    state=theme.public(datetime(2026,10,17,1,tzinfo=timezone.utc))
    assert datetime.fromisoformat(state['sunset']).date()==date(2026,10,16)
    summer=theme.public(datetime(2026,7,1,12,tzinfo=ZoneInfo(TIMEZONE)))
    winter=theme.public(datetime(2026,12,1,12,tzinfo=ZoneInfo(TIMEZONE)))
    assert datetime.fromisoformat(summer['sunrise']).utcoffset()==timedelta(hours=-2,minutes=-30)
    assert datetime.fromisoformat(winter['sunrise']).utcoffset()==timedelta(hours=-3,minutes=-30)
    with pytest.raises(ValueError):theme.public(datetime(2026,10,16))

def test_night_transform_preserves_base_and_maps_known_endpoints():
    base=Image.new('RGB',(2,1),'white');base.putpixel((1,0),(0,0,0))
    night=night_basemap(base)
    assert night.getpixel((0,0))==(20,40,58,255)
    assert night.getpixel((1,0))==(209,226,236,255)
    assert base.getpixel((0,0))==(255,255,255)

def test_theme_change_keeps_aircraft_history_and_uses_cached_night_base(tmp_path):
    renderer=MapRenderer(tmp_path,lambda:None)
    renderer.base=Image.new('RGBA',(3840,2160),'#b5d6e7')
    data={'healthy':True,'theme':{'effective':'day'},'aircraft':[{'lat':47.57,'lon':-52.8,'callsign':'TEST','altitude_ft':12000,'track':30,'trail':[],'stale':False}]}
    day,count=renderer.draw(data)
    data['theme']['effective']='night';night,count2=renderer.draw(data);cached=renderer.night_base
    renderer.draw(data)
    assert count==count2==1 and len(data['aircraft'])==1 and renderer.night_base is cached
    assert night.getpixel((0,0))!=day.getpixel((0,0))
    assert renderer.base.getpixel((0,0))==day.getpixel((0,0))

def test_theme_api_validates_and_keeps_map_data_available(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    monkeypatch.setattr(module,'map_theme',MapTheme(tmp_path))
    client=TestClient(module.app)
    assert client.put('/api/map/theme',json={'mode':'night'}).status_code==403
    headers={'X-Skycam-Edit':'1'}
    assert client.put('/api/map/theme',json={'mode':'invalid'},headers=headers).status_code==422
    response=client.put('/api/map/theme',json={'mode':'night'},headers=headers)
    assert response.status_code==200 and response.json()['effective']=='night'
    data=client.get('/api/map').json()
    assert data['theme']['effective']=='night' and isinstance(data['aircraft'],list)
    assert MapTheme(tmp_path).config.mode=='night'
