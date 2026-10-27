from types import SimpleNamespace
from skycam import playout as p


def isolate(monkeypatch):
    calls=[]
    monkeypatch.setitem(p.CAMERAS,'cam1',{**p.CAMERAS['cam1'],'enabled':True})
    monkeypatch.setattr(p,'command',calls.append)
    monkeypatch.setattr(p,'read_source_health',lambda:None)
    monkeypatch.setattr(p,'time',SimpleNamespace(monotonic=lambda:100.))
    for name in ('_last_used','_retry','_last','_changed','_advances','_native_metrics','_picture_policies','_recovery_badges','_slate_visible'):
        monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    monkeypatch.setattr(p,'_loaded',set())
    monkeypatch.setattr(p,'_slates',set(p.CAMERAS))
    return calls


def test_absent_source_keeps_scene_without_native_reconnect(monkeypatch):
    calls=isolate(monkeypatch)
    monkeypatch.setattr(p,'_source_health',{'cam1':{'ready':False}})
    monkeypatch.setattr(p,'reload_camera',lambda key:calls.append('RELOAD '+key))
    for i in range(10):p.ensure_inputs('cam1')
    assert calls==[] and p.available('cam1')
    p._source_health['cam1']['ready']=True
    p.ensure_inputs('cam1')
    assert calls==['RELOAD cam1']


def test_no_health_snapshot_does_not_launch_unverified_decoder(monkeypatch):
    calls=isolate(monkeypatch);monkeypatch.setattr(p,'_source_health',{})
    p.ensure_inputs('cam1');assert not calls


def test_dead_decoder_is_released_after_hold_not_30_second_retry(monkeypatch):
    calls=isolate(monkeypatch);p._loaded.add('cam1');p._retry['cam1']=95
    p._changed['cam1']=90;p._last['cam1']=4;p._advances['cam1']=2
    assert p.retire_stalled_input('cam1',99)
    assert calls[-1]==f'CLEAR {p.source_channel("cam1")}-10'
    assert all('1-5' not in c for c in calls)
    assert 'cam1' in p._slates and p._slate_visible['cam1']
    assert 'cam1' not in p._loaded and 'cam1' not in p._last
    assert p._retry['cam1']==95


def test_live_and_starting_decoders_are_not_retired(monkeypatch):
    calls=isolate(monkeypatch);p._loaded.update(('cam1','cam2'))
    p._retry.update(cam1=10,cam2=95);p._changed['cam1']=99
    assert not p.retire_stalled_input('cam1',100)
    assert not p.retire_stalled_input('cam2',100)
    assert not calls


def test_adopted_stalled_decoder_has_a_fixed_recovery_deadline(monkeypatch):
    calls=isolate(monkeypatch);p._loaded.add('cam1')
    for now in (100,103,108):assert not p.retire_stalled_input('cam1',now)
    assert p._retry['cam1']==100 and not calls
    assert p.retire_stalled_input('cam1',109)
    assert calls[-1]==f'CLEAR {p.source_channel("cam1")}-10'
    assert 'cam1' not in p._loaded
    assert not p.retire_stalled_input('cam1',110)
