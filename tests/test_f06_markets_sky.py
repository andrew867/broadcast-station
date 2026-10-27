from datetime import datetime,date,timezone
import math
import pytest
from astral import moon
from skycam.camera_recovery import PicturePolicy
from skycam.live_markets import LiveMarkets,MAX_AGE
from skycam.markets import Markets
from skycam import daylight

def test_hold_short_stalls_then_slate_and_require_stable_recovery():
    p=PicturePolicy()
    assert p.update(0,1,0,True)=='loading'
    assert p.update(1,30,0,True)=='loading'
    assert p.update(2,60,0,True)=='live'
    assert p.update(6,60,4,True)=='held'
    assert p.update(9,60,7,True)=='held'
    assert p.update(10,60,8,True)=='loading'
    assert p.update(11,61,0,True)=='loading'
    assert p.update(12,62,0,True)=='loading'
    assert p.update(13,63,0,True)=='live'
    assert p.update(14,1,0,True)=='loading' # decoder generation reset
    assert p.update(15,None,None,False)=='loading'

def test_recovery_is_labelled_and_single_or_static_picture_is_not_ready():
    p=PicturePolicy()
    for t in range(20):assert p.update(t,1,0,True,1)=='loading'
    assert p.update(20,2,0,True,1)=='loading'
    assert p.update(21,3,0,True,1)=='recovering'
    assert p.update(22,4,0,True,0)=='live'

def test_live_quotes_validate_order_source_timestamp_and_inversion():
    live=LiveMarkets('test')
    def message(p=1.4,t=1000000,s='OANDA:USD_CAD'):
        return {'type':'trade','data':[{'s':s,'p':p,'t':t}]}
    live.ingest(message(),1000)
    row=live.public(1001)['quotes']['fx']
    assert row['value']==pytest.approx(1/1.4) and row['observed_at']==1000
    for bad in (message(0),message(float('nan')),message(t=1100000),message(s='UNKNOWN'),message(1.9,t=990000)):
        live.ingest(bad,1001)
    assert live.public(1001)['quotes']['fx']['value']==row['value']
    assert not live.public(1000+MAX_AGE+1)['quotes']['fx']['available']
    assert live.public()['configured']
    assert 'test' not in str(live.public())

def test_stale_live_quotes_return_to_dated_reference_not_relabelled_live(tmp_path):
    markets=Markets(tmp_path);markets.live=LiveMarkets('')
    now=datetime(2026,10,18,20,tzinfo=timezone.utc).timestamp()
    markets.values={'fx':{'checked_at':now,'rows':[{'date':'2026-10-16','value':1.4}]}}
    markets.live.ingest({'type':'trade','data':[{'s':'OANDA:USD_CAD','p':1.5,'t':now*1000}]},now)
    assert markets.public(now)['cards'][0]['daily_reference'] is False
    row=markets.public(now+MAX_AGE+1)['cards'][0]
    assert row['daily_reference'] and row['date']=='2026-10-16'
    assert row['value']==pytest.approx(1/1.4)

def test_full_local_day_sky_curves_handle_dst_and_below_horizon():
    for day,hours in [(date(2026,3,8),23),(date(2026,11,1),25),(date(2026,10,18),24)]:
        points=daylight.sky_curve(day)
        assert len(points)==193
        assert points[-1]['at']-points[0]['at']==hours*3600
        assert all(math.isfinite(p[k]) and -90<=p[k]<=90 for p in points for k in ('sun','moon'))
        assert any(p['sun']<0 for p in points) and any(p['sun']>0 for p in points)
    now=datetime(2026,10,19,1,tzinfo=timezone.utc)
    data=daylight.public(now)
    assert data['moon_elevation']==pytest.approx(moon.elevation(daylight.OBSERVER,now))
    assert data['moon_azimuth']==pytest.approx(moon.azimuth(daylight.OBSERVER,now))

def test_filtered_duplicates_do_not_refresh_camera_age(monkeypatch):
    import xml.etree.ElementTree as ET
    from skycam import playout as p
    for name in ('_last','_changed','_advances','_retry','_native_metrics'):monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    for t in range(12):
        source=min(t,3)
        xml=ET.fromstring(f'<channel><layer_10><foreground><file><video-frame>{t*30}</video-frame><source-video-frame>{source}</source-video-frame></file></foreground></layer_10></channel>')
        p.observe_sources(xml,100+t,'cam1')
    assert not p.STATUS['cameras']['cam1']['ready']
    assert p.STATUS['cameras']['cam1']['frame_age_s']==8

def test_preview_preparation_uses_the_same_stability_gate(monkeypatch):
    import types,xml.etree.ElementTree as ET
    from skycam import playout as p
    tick=[0.0];counter=[0];shows=[]
    monkeypatch.setattr(p,'time',types.SimpleNamespace(monotonic=lambda:tick[0],time=lambda:100+tick[0],sleep=lambda n:tick.__setitem__(0,tick[0]+n)))
    for name in ('_last','_changed','_advances','_retry','_native_metrics','_picture_policies','_transport','_transport_recovered'):monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    monkeypatch.setattr(p,'_loaded',{'cam1'});monkeypatch.setattr(p,'_slate_visible',{'cam1':True})
    monkeypatch.setattr(p,'_recovery_badges',{'cam1':False})
    monkeypatch.setattr(p,'_source_health',{'cam1':{'ready':True}})
    monkeypatch.setattr(p,'read_source_health',lambda:None)
    monkeypatch.setattr(p,'required',lambda camera:{'cam1'})
    monkeypatch.setattr(p,'source_picture',lambda key,live:shows.append((tick[0],live)))
    def info(channel):
        counter[0]+=1
        return ET.fromstring(f'<channel><layer_10><foreground><file><video-frame>{counter[0]}</video-frame><source-video-frame>{counter[0]}</source-video-frame></file></foreground></layer_10></channel>')
    monkeypatch.setattr(p,'info',info)
    p.prime_inputs('cam1')
    assert len(shows)==1 and shows[0][1] and 2<=shows[0][0]<2.2
