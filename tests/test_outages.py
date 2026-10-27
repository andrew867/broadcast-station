import asyncio,json,time
import httpx,pytest
from skycam.outages import Outages,parse,fetch_layer,restoration,banner_image,outage_image
from skycam.program_clock import ProgramClock,ClockConfig,ClockRule
from skycam.native_ticker import NativeTicker
from skycam.broadcast import Broadcast
from skycam import playout

NOW=1792284000
def feature(planned=False,**updates):
    a={'ID':1,'OBJECTID':1,'CUSTOMER_COUNT':640,'POLYGONS_AFFECTED':"Power's Pond / TEST FIXTURE",'CAUSE':'Under investigation','TIME_OUTAGE':(NOW-3600)*1000,'TIME_RESTORED_EST':None,'TIME_BEGIN':(NOW-3600)*1000,'TIME_END':(NOW-30)*1000}
    a.update(updates);return {'attributes':a,'geometry':{'x':-52.8,'y':47.5}}

def provider(tmp_path):
    o=Outages(tmp_path);o.rows=parse([feature()],False,NOW);o.checked_at=NOW;o.verified=True;return o

def test_active_estimates_future_plans_staleness_and_restart(tmp_path):
    o=provider(tmp_path);o.rows+=parse([feature(TIME_BEGIN=(NOW+3600)*1000,TIME_END=(NOW+7200)*1000)],True,NOW)
    assert len(o.public(NOW)['active'])==1 and len(o.public(NOW)['upcoming'])==1
    assert o.banner(NOW) and not o.banner(NOW+31) and o.banner(NOW+601)
    assert not o.banner(NOW+1201)
    o.error='feed failed';assert not o.public(NOW)['fresh'] and not o.banner(NOW)
    assert o.public(NOW)['active'] # Failed check never means restored.
    row=parse([feature()],True,NOW)[0];assert restoration(row,NOW)=='Awaiting revised estimate'
    assert parse([feature(CUSTOMER_COUNT=0)],False,NOW)==[]
    assert not Outages(tmp_path).public(NOW)['fresh']
    for bad in (float('nan'),-1,'many'):
        with pytest.raises(ValueError):parse([feature(CUSTOMER_COUNT=bad)],False,NOW)

def test_pagination_errors_and_source_freshness(monkeypatch):
    monkeypatch.setattr('skycam.outages.time.time',lambda:NOW)
    def handler(request):
        if not request.url.path.endswith('/query'):return httpx.Response(200,json={'editingInfo':{'dataLastEditDate':NOW*1000},'dateFieldsTimeReference':{'timeZone':'UTC'}})
        offset=int(request.url.params['resultOffset']);f=feature(ID=offset+1,OBJECTID=offset+1)
        return httpx.Response(200,json={'features':[f],'exceededTransferLimit':offset==0,'spatialReference':{'wkid':4326}})
    async def run(handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:return await fetch_layer(client,0)
    assert len(asyncio.run(run(handler)))==2
    with pytest.raises(ValueError):asyncio.run(run(lambda request:httpx.Response(200,json={'error':{'message':'unavailable'}})))
    def stale(request):return httpx.Response(200,json={'editingInfo':{'dataLastEditDate':(NOW-4000)*1000},'dateFieldsTimeReference':{'timeZone':'UTC'}})
    with pytest.raises(ValueError):asyncio.run(run(stale))

def test_conditional_clock_skips_without_interrupting_background(tmp_path):
    from tests.test_program_clock import stamp,playlist,A
    c=ProgramClock(tmp_path,playlist,now=stamp(11,59));c.config=ClockConfig(enabled=True,rules=[ClockRule(id='outages',playlist_id=A,every_minutes=10,condition='power-outages')])
    assert c.upcoming(stamp(11,59)) is None
    assert c.claim_due(now=stamp()+1) is None and c.history[-1]['outcome']=='skipped_condition'
    c.eligible=lambda _:True
    assert c.claim_due(now=stamp(12,10)+1)['name']=='Short'

def test_official_emergency_preempts_outage_and_no_video_audio_commands(tmp_path,monkeypatch):
    from tests.test_alert_playout import alert_row
    o=provider(tmp_path);state={'immediate':[],'fresh':True};calls=[]
    monkeypatch.setattr(playout,'command',lambda text,**kw:calls.append(text) or '202 OK')
    t=NativeTicker(tmp_path,Broadcast(tmp_path),lambda:state,lambda:o.banner(NOW))
    assert t.emergency(1) and t.status['outage_banner']
    state['immediate']=[alert_row(tmp_path)]
    assert t.emergency(2) and t.status['emergency']
    assert all(21<=int(c.split()[1].split('-')[1])<=41 for c in calls)
    assert banner_image(o.banner(NOW)).size==(3840,224)
    assert outage_image(o.public(NOW),0).size==(3840,2160)

def test_api_guard_and_image(tmp_path,monkeypatch):
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    from fastapi.testclient import TestClient
    o=provider(tmp_path);monkeypatch.setattr(module,'outages',o)
    client=TestClient(module.app)
    assert client.put('/api/outages',json={}).status_code==403
    assert client.put('/api/outages',json={'banner_enabled':False},headers={'X-Skycam-Edit':'1'}).status_code==200
    assert not o.config.banner_enabled
