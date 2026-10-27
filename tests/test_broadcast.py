import time
import pytest
from skycam.broadcast import Broadcast, BroadcastState

def test_news_stale_cache_and_publication_expire(tmp_path):
    b=Broadcast(tmp_path);now=time.time()
    b.news['cbc_nl']={'fetched_at':now,'items':[
        {'title':'Fresh','published_at':now-60},
        {'title':'Old','published_at':now-37*3600},
        {'title':'Future','published_at':now+600}]}
    assert [p['title'] for p in b.public()['headlines']]==['Fresh']
    b.news['cbc_nl']['fetched_at']=now-1801
    assert b.public()['headlines']==[]

def test_broadcast_state_roundtrip_and_unknown_source(tmp_path):
    b=Broadcast(tmp_path)
    b.save(BroadcastState(camera='cam4',scene='breaking',ticker_speed=120))
    assert Broadcast(tmp_path).state.camera=='cam4'
    with pytest.raises(ValueError):b.save(BroadcastState(news_sources=['made_up']))
    assert Broadcast(tmp_path).state.camera=='cam4'


def test_all_selected_news_sources_get_ticker_space(tmp_path):
    from skycam.broadcast import SOURCES
    b=Broadcast(tmp_path);now=time.time();b.state.news_sources=list(SOURCES)
    for key,(name,_) in SOURCES.items():
        b.news[key]={'fetched_at':now,'items':[{'title':f'{key} item {i}','source':name,'published_at':now-i} for i in range(25)]}
    assert {x['source'] for x in b.public()['headlines']}=={v[0] for v in SOURCES.values()}


def test_rundown_deadline_manual_hold_and_failure(tmp_path,monkeypatch):
    from skycam.rundown import Rundown,RundownConfig,Cue
    calls=[];clock=[100.]
    monkeypatch.setattr('skycam.rundown.time.monotonic',lambda:clock[0])
    r=Rundown(tmp_path,lambda *args:calls.append(args))
    r.save(RundownConfig(cues=[Cue(camera='cam1',seconds=5),Cue(camera='quad',seconds=10)]))
    r.action('start');assert calls[-1][0]=='cam1'
    clock[0]=104.9;r.advance_due();assert len(calls)==1
    clock[0]=105.;r.advance_due();assert calls[-1][0]=='quad'
    r.pause();clock[0]=200;r.advance_due();assert len(calls)==2
    def failed(*_):raise RuntimeError('Disconnected')
    r.apply=failed
    r.action('start')
    assert r.enabled and r.error=='Disconnected'
    assert r.deadline==205
    assert Rundown(tmp_path,lambda *_:None).config.cues[1].camera=='quad'

def test_rundown_skips_failed_camera_and_continues(tmp_path):
    from skycam.rundown import Rundown,RundownConfig,Cue
    calls=[]
    r=Rundown(tmp_path,lambda *args:calls.append(args),lambda c:c!='cam3')
    r.save(RundownConfig(cues=[Cue(camera='cam3'),Cue(camera='cam4')]))
    r.action('start')
    assert r.enabled and r.index==1 and calls==[('cam4','standard',30)]
    assert 'skipped cam3' in r.note

def test_rundown_take_race_falls_through_to_next_source(tmp_path):
    from skycam.rundown import Rundown,RundownConfig,Cue
    calls=[]
    def apply(camera,*args):
        if camera=='cam1':raise RuntimeError('Lost frame just before take')
        calls.append(camera)
    r=Rundown(tmp_path,apply)
    r.save(RundownConfig(cues=[Cue(camera='cam1'),Cue(camera='cam2')]))
    r.action('start')
    assert r.enabled and calls==['cam2']

def test_source_readiness_requires_recent_advancing_delivered_video(monkeypatch):
    import xml.etree.ElementTree as ET
    from skycam import playout as p
    for name in ['_last','_changed','_advances','_retry']:monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    def frame(t):return ET.fromstring(f'<channel><layer_10><foreground><file><video-frame>{t}</video-frame></file></foreground></layer_10></channel>')
    p.observe_sources(frame(10),100)
    assert not p.STATUS['cameras']['cam1']['ready']
    p.observe_sources(frame(10.5),100.5)
    p.observe_sources(frame(11),101)
    assert p.STATUS['cameras']['cam1']['ready']
    p.observe_sources(frame(11),104)
    assert not p.STATUS['cameras']['cam1']['ready']
