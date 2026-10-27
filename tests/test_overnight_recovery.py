import xml.etree.ElementTree as ET
from skycam import playout as p
from skycam.resource_budget import GraphicsBudget,MIB
from skycam.readiness import program_moving,snapshot

def test_advancing_audio_or_eof_time_never_proves_video(monkeypatch):
    for name in ['_last','_changed','_advances','_retry']:monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    def frame(t,v):return ET.fromstring(f'<channel><layer_10><foreground><file><time>{t}</time><video-frame>{v}</video-frame></file></foreground></layer_10></channel>')
    for t in range(5):p.observe_sources(frame(t,0),100+t,'cam1')
    assert not p.STATUS['cameras']['cam1']['ready']
    for t in range(5,8):p.observe_sources(frame(t,t),100+t,'cam1')
    assert p.STATUS['cameras']['cam1']['ready']
    p.observe_sources(frame(12,7),112,'cam1')
    assert not p.STATUS['cameras']['cam1']['ready']
    p.observe_sources(frame(13,1),113,'cam1')
    assert p._advances['cam1']==0

def test_missing_video_counter_fails_closed(monkeypatch):
    for name in ['_last','_changed','_advances','_retry']:monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    for n in range(4):
        p.observe_sources(ET.fromstring(f'<channel><layer_10><foreground><file><time>{n}</time></file></foreground></layer_10></channel>'),100+n,'cam1')
    assert not p.STATUS['cameras']['cam1']['ready']

def pools(device=0,host=0,allocated=0,budget=384*MIB):
    return f'201 GL INFO OK\r\n<?xml version="1.0"?><gl><summary><cache_budget_bytes>{budget}</cache_budget_bytes><pooled_device_buffers><total_size>{device}</total_size></pooled_device_buffers><pooled_host_buffers><total_read_size>{host}</total_read_size><total_write_size>0</total_write_size></pooled_host_buffers><all_host_buffers><total_read_size>{allocated}</total_read_size></all_host_buffers></summary></gl>'

def test_resource_observer_is_read_only_and_polls_at_bounded_rate():
    calls=[];reply=[pools(0,0,4*1024*MIB)]
    def command(text,**kwargs):calls.append(text);return reply[0] if text=='GL INFO' else '202 GL GC OK'
    budget=GraphicsBudget();budget.check(command,100)
    assert calls==['GL INFO']
    assert budget.status['budget_per_pool_bytes']==384*MIB
    reply[0]=pools(500*MIB);budget.check(command,110);assert len(calls)==1
    budget.check(command,130);budget.check(command,160);budget.check(command,250)
    assert calls==['GL INFO']*4  # Never perform bulk GC on the live engine.

def test_failed_measurement_is_reported_without_failing_playout():
    def failed(*args,**kwargs):raise OSError('engine busy')
    budget=GraphicsBudget();assert budget.check(failed,100)['error']=='engine busy'

def test_older_engine_without_budget_is_reported():
    budget=GraphicsBudget();result=budget.check(lambda *args,**kwargs:pools(budget=0),100)
    assert 'unavailable' in result['error']

def test_missing_output_status_is_not_a_health_crash():
    assert not program_moving({'connected':True,'ready':True,'checked_at':100,'output':None},101)

def test_amcp_failure_with_null_output_remains_recoverable(monkeypatch):
    monkeypatch.setattr(p,'STATUS',{'output':None})
    monkeypatch.setattr(p,'_ready',True)
    def unavailable(*args):raise OSError('temporarily unreachable')
    monkeypatch.setattr(p,'info',unavailable)
    assert p.check(None) is None
    assert p.STATUS['output']['moving'] is False
    assert not p.STATUS['ready']

def test_idle_map_is_standby_but_active_stale_map_is_a_warning():
    status={'program':{'camera':'cam1'}}
    maps={'map':{'ready':True,'updated_at':1},'map-island':{'ready':True,'updated_at':1}}
    def checks():return {c['id']:c for c in snapshot(status,{},maps['map'],{},{},now=100,map_states=maps)['checks']}
    assert checks()['map']['level']=='ok'
    status['program']['camera']='map-island'
    assert checks()['map']['level']=='ok'
    assert checks()['map-island']['level']=='warning'
    maps['map-island']['updated_at']=99
    assert checks()['map-island']['level']=='ok'
    maps['map']['error']='failed to render'
    assert checks()['map']['level']=='warning'

def test_weather_refresh_cadence_and_prepared_map_are_checked():
    status={'program':{'camera':'weather'},'preview':{'camera':'radar-east'}}
    maps={'weather':{'ready':True,'updated_at':70},'radar-east':{'ready':True,'updated_at':70}}
    checks={c['id']:c for c in snapshot(status,{},{},{},{},now=100,map_states=maps)['checks']}
    assert checks['weather']['level']=='ok'
    assert checks['radar-east']['level']=='warning'
