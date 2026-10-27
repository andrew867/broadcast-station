import pytest
from skycam import playout
from skycam.music import Music,MusicConfig
from skycam.broadcast import Broadcast,BroadcastState
from skycam.native_ticker import NativeTicker

def test_volume_does_not_restart_current_track(tmp_path,monkeypatch):
    calls=[];monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'command',lambda c:calls.append(c))
    m=Music(tmp_path);m.current='playing.wav';m.queued='next.wav'
    m.save(MusicConfig(volume=.73))
    assert m.current=='playing.wav' and m.queued=='next.wav'
    assert calls==[f'MIXER 1-5 VOLUME 0.73 {playout.PROGRAM_FPS//2} LINEAR']

def test_track_selection_history_shuffle_and_validation(tmp_path,monkeypatch):
    calls=[];monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'command',lambda c:calls.append(c))
    m=Music(tmp_path);m.files=['a.wav','b.wav','c.wav'];m.current='a.wav';m.queued='b.wav'
    monkeypatch.setattr(m,'check',lambda:None)
    m.action('next');assert m.current=='b.wav'
    m.action('previous');assert m.current=='a.wav'
    m.action('play','c.wav');assert m.current=='c.wav'
    count=len(calls)
    with pytest.raises(ValueError):m.action('play','../../secret.wav')
    assert len(calls)==count
    m.config.shuffle=True
    assert all(m.pick_next('c.wav') in {'a.wav','b.wav'} for _ in range(30))

def test_dead_sources_do_not_make_scenes_unavailable(monkeypatch):
    monkeypatch.setattr(playout,'STATUS',{'cameras':{}})
    for camera in ['cam1','cam2','cam3','cam4','quad','map']:assert playout.available(camera)
    assert not playout.available('unknown')

def test_scene_take_keeps_required_inputs_then_trims_idle_decoders(monkeypatch):
    import xml.etree.ElementTree as ET
    calls=[]
    monkeypatch.setattr(playout,'_retiring',None)
    monkeypatch.setattr(playout,'info',lambda channel:ET.fromstring('<channel><layer_10><foreground><route><channel>3</channel></route></foreground></layer_10></channel>'))
    monkeypatch.setattr(playout,'ENABLED',True)
    monkeypatch.setattr(playout,'_bank',2)
    monkeypatch.setattr(playout,'_camera','quad')
    monkeypatch.setattr(playout,'_prepared',None)
    monkeypatch.setattr(playout,'_loaded',{'cam1','cam2','cam3','cam4'})
    monkeypatch.setattr(playout,'_last_used',{'cam1':1,'cam2':2,'cam3':3,'cam4':4})
    monkeypatch.setattr(playout,'_slates',set())
    monkeypatch.setattr(playout,'STATUS',{})
    monkeypatch.setattr(playout,'command',lambda c:calls.append(c))
    monkeypatch.setattr(playout,'prepare',lambda camera,state:{'bank':3,'camera':camera})
    playout.release_unused()
    assert playout._loaded=={'cam1','cam2','cam3','cam4'} and not calls
    playout.take('map',frames=0,state=BroadcastState(camera='map'))
    assert playout._loaded==set()
    assert calls[:2]==['PLAY 1-10','CLEAR 2']
    assert set(calls[2:])=={'CLEAR 4-10','CLEAR 5-10','CLEAR 6-10','CLEAR 7-10'}

def test_ticker_expiry_settings_and_proportions(tmp_path,monkeypatch):
    calls=[];clock=[100.];b=Broadcast(tmp_path)
    monkeypatch.setattr(playout,'STATUS',{'ready':True})
    def command(c,**kw):
        calls.append(c)
        if c.endswith(' FILL'):return '201 MIXER OK\r\n1 0.896296 0.5 0.085185\r\n'
    monkeypatch.setattr(playout,'command',command)
    monkeypatch.setattr('skycam.native_ticker.time.monotonic',lambda:clock[0])
    state=BroadcastState().model_dump()
    payload={'state':state,'headlines':[{'source':'A','title':'First headline'}]}
    monkeypatch.setattr(b,'public',lambda:payload)
    t=NativeTicker(tmp_path,b);t.tick()
    from PIL import Image
    strip=next(p for p in (tmp_path/'ticker').glob('*.png') if Image.open(p).width!=3840)
    width,height=Image.open(strip).size
    assert width<3400  # Short items must not reserve a fixed-width blank tail.
    assert t.next_at==pytest.approx(100+(width+96)/state['ticker_speed'])
    fills=[c.split() for c in calls if c.startswith('MIXER 1-22 FILL')]
    assert float(fills[0][5])*3840/width==pytest.approx(1)
    assert float(fills[0][6])*2160/height==pytest.approx(1)
    calls.clear();clock[0]+=1;t.tick();assert calls==['MIXER 1-22 FILL']
    state['ticker_speed']=120;t.tick();assert any(c.startswith('PLAY 1-22 ') for c in calls)
    calls.clear();payload['headlines']=[{'source':'B','title':'Replacement'}];t.tick()
    assert 'CLEAR 1-22' in calls and 'CLEAR 1-23' in calls
    assert t.status['headline']=='Replacement'
    calls.clear();state['show_ticker']=False;t.tick()
    assert set(calls)=={f'CLEAR 1-{i}' for i in range(21,41)}

def test_map_keeps_stale_positions_when_receiver_drops(monkeypatch):
    from skycam import app as a
    from collections import deque
    from types import SimpleNamespace
    p={'time':94.,'hex':'abc123','callsign':'TEST','lat':47.,'lon':-52.,'track':90,'altitude_ft':12000}
    monkeypatch.setattr(a,'tracks',SimpleNamespace(history={'abc123':deque([p])},status=lambda now:{'healthy':False}))
    monkeypatch.setattr(a.time,'time',lambda:100.)
    data=a.map_data();assert len(data['aircraft'])==1 and data['aircraft'][0]['stale']
    monkeypatch.setattr(a.time,'time',lambda:155.)
    assert a.map_data()['aircraft']==[]
def test_map_labels_do_not_overlap_reserved_panels_or_other_labels():
    from skycam.map_renderer import label_box
    boxes=[(2940,90,3730,500)]
    for x,y in [(3000,310),(3002,312),(3005,308),(3010,315)]:
        box=label_box(x,y,350,boxes)
        assert box is not None
        a,b,c,d=box
        assert all(c+8<x1 or a>x2+8 or d+8<y1 or b>y2+8 for x1,y1,x2,y2 in boxes)
        boxes.append(box)

def test_music_waits_for_selected_producer_before_adopting_old_info(tmp_path,monkeypatch):
    from pathlib import Path
    calls=[];monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    m=Music(tmp_path);m.folder=tmp_path
    (tmp_path/'a.wav').touch();(tmp_path/'b.wav').touch()
    m.current='b.wav';m.pending=('b.wav',100.)
    monkeypatch.setattr('skycam.music.time.monotonic',lambda:101.)
    def command(c,**kw):
        calls.append(c)
        return '<?xml version="1.0"?><channel><layer_5><foreground><file><path>/workspace/media/music/a.wav</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command)
    m.check()
    assert m.current=='b.wav' and m.pending==('b.wav',100.)
    assert calls==['INFO 1']
def test_aircraft_graphics_fail_closed_and_use_engine_expiry(tmp_path,monkeypatch):
    from skycam.aircraft_graphics import AircraftGraphics
    from types import SimpleNamespace
    from skycam.broadcast import BroadcastState
    calls=[]
    monkeypatch.setattr(playout,'STATUS',{'ready':True,'cameras':{'cam1':{'native_ready':True}}})
    monkeypatch.setattr(playout,'_camera','cam1');monkeypatch.setattr(playout,'_prepared',None)
    monkeypatch.setattr(playout,'command',lambda c:calls.append(c))
    b=SimpleNamespace(state=BroadcastState(show_aircraft=True))
    payload={'state':'uncalibrated','labels':[]}
    renderer=AircraftGraphics(tmp_path,b,lambda _:payload)
    renderer.tick();assert calls==[]
    payload.update(state='live',width=2688,height=1520,labels=[{'x':1344,'y':760,'callsign':'TEST','altitude_ft':10000,'range_km':15,'mode':'interpolated'}])
    renderer.tick()
    assert calls[0].startswith('PLAY 4-15 ') and calls[0].endswith(' LENGTH 18')
    assert calls[1].endswith('transparent.png" AUTO')
    calls.clear();payload['state']='feed_unavailable';renderer.tick()
    assert calls==['CLEAR 4-15']
    calls.clear();payload['state']='live';playout.STATUS['cameras']['cam1']['native_ready']=False;renderer.tick()
    assert calls==[]
