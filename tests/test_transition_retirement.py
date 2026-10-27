import xml.etree.ElementTree as ET
import pytest
from skycam import playout


def native(transition=False, channel=3):
    content='<transition><frame>12</frame></transition>' if transition else f'<route><channel>{channel}</channel></route>'
    return ET.fromstring(f'<channel><layer_10><foreground>{content}</foreground></layer_10></channel>')


@pytest.fixture(params=[30,60])
def handover(monkeypatch,request):
    clock=[100.];calls=[]
    monkeypatch.setattr(playout.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(playout.time,'sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    monkeypatch.setattr(playout,'STATUS',{})
    monkeypatch.setattr(playout,'_camera','map')
    monkeypatch.setattr(playout,'PROGRAM_FPS',request.param)
    monkeypatch.setattr(playout,'_retiring',{'bank':2,'camera':'quad','destination':3,'frames':request.param//2,'started':100.})
    monkeypatch.setattr(playout,'command',calls.append)
    return clock,calls


def test_normal_dissolve_retires_only_after_route_confirmation(handover,monkeypatch):
    clock,calls=handover
    def info(channel):
        assert not calls
        return native(transition=clock[0]<100.6)
    monkeypatch.setattr(playout,'info',info)
    playout.finish_handover()
    assert calls==['CLEAR 2']
    assert playout._retiring is None
    assert not playout.STATUS['transition']['fallback_cut']


def test_slow_dissolve_cuts_to_prepared_bank_before_clearing_old(handover,monkeypatch):
    clock,calls=handover
    monkeypatch.setattr(playout,'info',lambda channel:native(transition='PLAY 1-10' not in calls))
    playout.finish_handover()
    assert calls==['LOADBG 1-10 route://3','PLAY 1-10','CLEAR 2']
    assert 1<=playout.STATUS['transition']['seconds']<1.2
    assert playout.STATUS['transition']['fallback_cut']


def test_failed_confirmation_retains_old_bank_and_decoders(handover,monkeypatch):
    clock,calls=handover
    monkeypatch.setattr(playout,'info',lambda channel:native(transition=True))
    with pytest.raises(RuntimeError,match='retained'):playout.finish_handover()
    assert not any(c.startswith('CLEAR') for c in calls)
    monkeypatch.setattr(playout,'_prepared',None)
    monkeypatch.setattr(playout,'_loaded',{'cam1','cam2','cam3','cam4'})
    monkeypatch.setattr(playout,'_last_used',{})
    playout.release_unused()
    assert playout._loaded=={'cam1','cam2','cam3','cam4'}
    monkeypatch.setattr(playout,'_ready',True)
    with pytest.raises(RuntimeError,match='retained'):playout.prepare('map',None)
    assert not any(c.startswith('CLEAR') for c in calls)
    monkeypatch.setattr(playout,'info',lambda channel:native())
    playout.finish_handover()
    assert calls[-1]=='CLEAR 2' and playout._retiring is None
    assert playout.STATUS['transition']['fallback_cut']


def test_wrong_route_is_not_confirmation(handover,monkeypatch):
    monkeypatch.setattr(playout,'info',lambda channel:native(channel=2))
    with pytest.raises(RuntimeError,match='retained'):playout.finish_handover()
    assert 'CLEAR 2' not in handover[1]


def test_handover_history_is_bounded(handover,monkeypatch):
    monkeypatch.setattr(playout,'info',lambda channel:native())
    playout.STATUS['transition_history']=[{'old':n} for n in range(24)]
    playout.finish_handover()
    assert len(playout.STATUS['transition_history'])==24
    assert playout.STATUS['transition_history'][0]=={'old':1}


def test_camera_reload_uses_configured_transport_without_changing_source_health(monkeypatch):
    calls=[]
    monkeypatch.setattr(playout,'CAMERA_TRANSPORT','rtsp')
    monkeypatch.setattr(playout,'command',calls.append)
    monkeypatch.setattr(playout,'source_picture',lambda *args:None)
    monkeypatch.setattr(playout,'_loaded',set())
    for key in ['_retry','_last','_advances','_changed']:
        monkeypatch.setattr(playout,key,{})
    playout.reload_camera('cam2')
    assert len(calls)==1 and playout.CAMERAS['cam2']['rtsp'] in calls[0]
    assert 'cam2' in playout._loaded and playout._advances['cam2']==0
