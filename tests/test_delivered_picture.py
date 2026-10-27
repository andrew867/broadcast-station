"""A background decoder must not conceal a frozen playout picture."""
import xml.etree.ElementTree as ET
import pytest
from skycam import playout as p

@pytest.fixture
def observe(monkeypatch):
    for name in ('_last','_changed','_advances','_retry','_delivery_progress','_native_metrics'):
        monkeypatch.setattr(p,name,{})
    monkeypatch.setattr(p,'STATUS',{'cameras':{}})
    def check(at,decoded,delivered):
        fields=f'<source-video-frame>{decoded}</source-video-frame>'
        if delivered is not None:fields+=f'<video-frame>{delivered}</video-frame>'
        p.observe_sources(ET.fromstring(f'<channel><layer_10><foreground><file>{fields}</file></foreground></layer_10></channel>'),at,'cam1')
        return p.STATUS['cameras']['cam1']
    return check

def test_background_decode_cannot_refresh_paused_picture(observe):
    for t in range(4):state=observe(100+t,t*30,t*30)
    assert state['ready']
    for t in range(4,14):state=observe(100+t,t*30,90)
    assert not state['ready'] and state['stalled_seconds']==10
    assert p._changed['cam1']==103
    for t in range(14,17):state=observe(100+t,t*30,t*30)
    assert state['ready']

def test_output_duplicates_cannot_refresh_stopped_decoder(observe):
    for t in range(4):observe(100+t,t*30,t*30)
    for t in range(4,14):state=observe(100+t,90,t*30)
    assert not state['ready'] and state['stalled_seconds']==10

def test_missing_delivery_and_counter_reset_fail_closed(observe):
    for t in range(4):observe(100+t,t*30,t*30)
    assert not observe(104,120,None)['ready']
    assert not observe(105,150,1)['ready']
    assert not observe(106,180,31)['ready']
    assert observe(107,210,61)['ready']
    assert not observe(108,240,0)['ready']
