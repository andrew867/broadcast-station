from skycam import playout
from skycam.broadcast import Broadcast
from skycam.native_ticker import NativeTicker
import pytest


@pytest.mark.parametrize('observed_disconnect',[False,True])
def test_engine_replacement_restores_crawl_even_when_controller_survives(tmp_path,monkeypatch,observed_disconnect):
    calls=[]
    def command(value,**kwargs):
        calls.append(value)
        return '201 MIXER OK\r\n1 0.9 0.5 0.1\r\n'
    monkeypatch.setattr(playout,'STATUS',{'ready':True,'graphics_epoch':1})
    monkeypatch.setattr(playout,'command',command)
    ticker=NativeTicker(tmp_path,Broadcast(tmp_path));ticker.tick();calls.clear()
    if observed_disconnect:
        playout.STATUS['ready']=False;ticker.tick();assert calls==[]
    playout.STATUS.update(ready=True,graphics_epoch=2);ticker.tick()
    for layer in (21,22,40):assert any(c.startswith(f'PLAY 1-{layer} ') for c in calls)
    assert not any(c.startswith(('CLEAR 1-5 ','PLAY 1-5 ','CLEAR 1-10 ','PLAY 1-10 ')) for c in calls)
    calls.clear();ticker.tick()
    assert not any(c.startswith('PLAY 1-21 ') for c in calls)


def test_native_rebuild_advances_graphics_epoch(monkeypatch):
    import xml.etree.ElementTree as ET
    from skycam.broadcast import BroadcastState
    root=ET.fromstring('<channel><output><port><port_1/><port_3/></port></output></channel>')
    monkeypatch.setattr(playout,'STATUS',{'graphics_epoch':3})
    monkeypatch.setattr(playout,'CAMERAS',{})
    for name in ('_ready','_bank','_camera','_prepared','_retiring'):
        monkeypatch.setattr(playout,name,getattr(playout,name))
    monkeypatch.setattr(playout,'_loaded',set());monkeypatch.setattr(playout,'_slates',set())
    monkeypatch.setattr(playout,'ensure_inputs',lambda camera:None)
    monkeypatch.setattr(playout,'release_unused',lambda:None)
    playout.bootstrap(BroadcastState(),root)
    assert playout.STATUS['graphics_epoch']==4
