import json
import pytest
from PIL import Image,ImageChops
from skycam.sources import CameraCatalog,CameraSpec
from skycam.broadcast import BroadcastState
from skycam.map_theme import MapTheme,MapThemeRequest
from skycam.map_renderer import MapRenderer

def test_inventory_persistence_slots_credits_and_crud(tmp_path):
    c=CameraCatalog(tmp_path);c.initialize()
    assert len(c.cameras)==8 and 8 not in [r['channel'] for r in c.cameras.values()]
    assert c.cameras['cam3']['attribution_text']==''
    assert c.cameras['ntv-cam4']['attribution_text']==''
    spec=CameraSpec(id='test-feed',name='Test',media_path='test-feed',enabled=False)
    added=c.create(spec);assert added['channel']==13
    c.update(spec.id,spec.model_copy(update={'name':'Changed','attribution_enabled':True,'attribution_text':'Courtesy Test'}))
    assert CameraCatalog(tmp_path).cameras[spec.id]['name']=='Changed'
    c.delete(spec.id)
    with pytest.raises(ValueError):c.create(spec)
    assert CameraCatalog(tmp_path).retired==['test-feed']

def test_quad_guards_and_order(tmp_path):
    c=CameraCatalog(tmp_path)
    with pytest.raises(ValueError):c.delete('ntv-cam1')
    with pytest.raises(ValueError):c.save_quad('quad2',['cam1']*4)
    ids=['ntv-cam4','ntv-cam3','ntv-cam2','ntv-cam1'];c.save_quad('quad2',ids)
    assert CameraCatalog(tmp_path).quads['quad2']==ids
    with pytest.raises(ValueError):CameraSpec(id='map',name='Map',media_path='map')
    with pytest.raises(ValueError):CameraSpec(id='okay',name='Test',media_path='bad"command')

def test_quad_routes_slots_and_cache_order(monkeypatch):
    from skycam import playout
    commands=[]
    monkeypatch.setattr(playout,'command',commands.append)
    monkeypatch.setattr(playout,'ensure_inputs',lambda c:None)
    monkeypatch.setattr(playout,'render',lambda state:__import__('pathlib').Path('test.png'))
    monkeypatch.setattr(playout,'_ready',True);monkeypatch.setattr(playout,'_bank',2);monkeypatch.setattr(playout,'_prepared',None)
    s=BroadcastState(camera='quad2');key=playout.state_key(s);playout.prepare('quad2',s)
    assert [v for v in commands if v.startswith('PLAY 3-1')]==[f'PLAY 3-{10+i} route://{9+i}' for i in range(4)]
    assert 'MIXER 3-13 FILL 0.5 0.5 .5 .5' in commands
    monkeypatch.setitem(playout.QUADS,'quad2',list(reversed(playout.QUADS['quad2'])))
    assert key!=playout.state_key(s)

def test_attribution_renders_and_follows_quad_order(tmp_path,monkeypatch):
    from skycam import graphics
    monkeypatch.setattr(graphics,'DATA',tmp_path)
    monkeypatch.setitem(graphics.CAMERAS,'cam3',{**graphics.CAMERAS['cam3'],'attribution_enabled':True,'attribution_text':'Courtesy Test'})
    state=BroadcastState(camera='cam3');shown=graphics.render(state)
    monkeypatch.setitem(graphics.CAMERAS,'cam3',{**graphics.CAMERAS['cam3'],'attribution_enabled':False})
    hidden=graphics.render(state)
    with Image.open(shown) as a,Image.open(hidden) as b:
        box=ImageChops.difference(a,b).getbbox()
        assert box is not None and box[1:4:2]==(1433,1500) and box[2]==3649
    state=BroadcastState(camera='quad2');first=graphics.render(state)
    monkeypatch.setitem(graphics.QUADS,'quad2',list(reversed(graphics.QUADS['quad2'])))
    assert first!=graphics.render(state)

def test_map_bug_hide_preserves_plane_labels(tmp_path,monkeypatch):
    renderer=MapRenderer(tmp_path,lambda:None);renderer.base=Image.new('RGBA',(3840,2160),'#b5d6e7')
    data={'healthy':True,'theme':{'show_info':True},'aircraft':[{'lat':47.57,'lon':-52.8,'callsign':'TEST123','altitude_ft':12000,'track':30,'trail':[],'stale':False}]}
    labels=[]
    from PIL import ImageDraw
    original=ImageDraw.ImageDraw.text
    def record(self,xy,text,*args,**kwargs):labels.append(text);return original(self,xy,text,*args,**kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw,'text',record)
    shown,_=renderer.draw(data);fresh=[s for s in labels if 'TEST123' in s]
    labels.clear();data['theme']['show_info']=False;data['aircraft'][0]['stale']=True
    hidden,_=renderer.draw(data);stale=[s for s in labels if 'TEST123' in s]
    assert fresh==stale and not any('LAST SEEN' in s for s in labels)
    assert hidden.getpixel((3000,300))==renderer.base.getpixel((3000,300))!=shown.getpixel((3000,300))
    theme=MapTheme(tmp_path);theme.save(MapThemeRequest(mode='auto',show_info=False));assert MapTheme(tmp_path).public()['show_info'] is False


def test_camera_api_edit_guards_and_calibration_invalidation(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    c=CameraCatalog(tmp_path)
    monkeypatch.setattr(module,'DATA',tmp_path);monkeypatch.setattr(module,'CATALOG',c);monkeypatch.setattr(module,'CAMERAS',c.cameras);monkeypatch.setattr(module,'QUADS',c.quads)
    monkeypatch.setattr(module.playout,'ENABLED',False);monkeypatch.setattr(module.playout,'CAMERAS',c.cameras);monkeypatch.setattr(module.playout,'QUADS',c.quads)
    client=TestClient(module.app);headers={'X-Skycam-Edit':'1'}
    assert client.delete('/api/source-catalog/ntv-cam1',headers=headers).status_code==409
    spec=CameraSpec(id='api-test',name='API Test',media_path='unused',enabled=False).model_dump()
    assert client.post('/api/source-catalog',json=spec).status_code==403
    assert client.post('/api/source-catalog',json=spec,headers=headers).status_code==200
    profile=tmp_path/'api-test.json';saved=json.loads(profile.read_text());saved['request']['approved']=True;profile.write_text(json.dumps(saved))
    spec['media_path']='unused-new'
    assert client.put('/api/source-catalog/api-test',json=spec,headers=headers).status_code==200
    saved=json.loads(profile.read_text());assert saved['request']['approved'] is False and saved['calibration'] is None
    assert client.delete('/api/source-catalog/api-test',headers=headers).status_code==200
    assert not profile.exists() and list((tmp_path/'revisions').glob('deleted-api-test-*.json'))
    assert list((tmp_path/'revisions').glob('api-test-*.json'))

def test_decoder_cache_never_evicts_program_or_preview_and_clears_retry(monkeypatch):
    from skycam import playout as p
    calls=[];monkeypatch.setattr(p,'command',calls.append)
    monkeypatch.setattr(p,'_loaded',set(p.CAMERAS));monkeypatch.setattr(p,'_last_used',{})
    monkeypatch.setattr(p,'_slates',set());monkeypatch.setattr(p,'_retry',{k:100 for k in p.CAMERAS})
    monkeypatch.setattr(p,'_camera','quad');monkeypatch.setattr(p,'_prepared',{'camera':'quad2'})
    p.release_unused();assert len(p._loaded)==8 and not calls
    monkeypatch.setattr(p,'_camera','quad2');monkeypatch.setattr(p,'_prepared',None)
    p.release_unused();assert p._loaded==set(p.QUADS['quad2'])
    assert set(calls)=={f'CLEAR {n}-10' for n in (4,5,6,7)}
    assert all(k not in p._retry for k in ('cam1','cam2','cam3','cam4'))

def test_disconnected_input_does_not_wait_or_block_scene(monkeypatch):
    from skycam import playout as p
    monkeypatch.setattr(p,'_loaded',{'cam3'});monkeypatch.setattr(p,'_source_health',{'cam3':{'ready':False}})
    monkeypatch.setattr(p,'read_source_health',lambda:None)
    def unexpected(*args):raise AssertionError('Disconnected input should not block scene preparation')
    monkeypatch.setattr(p,'info',unexpected);p.prime_inputs('cam3')

def test_ticker_spacing_uses_real_position_when_frames_slow(tmp_path,monkeypatch):
    from skycam.native_ticker import NativeTicker,ITEM_GAP
    from skycam.broadcast import Broadcast
    from skycam import playout
    calls=[];clock=[100.];position=[1.,.5]
    from datetime import datetime
    from types import SimpleNamespace
    monkeypatch.setattr('skycam.native_ticker.datetime',SimpleNamespace(now=lambda zone:datetime(2026,10,19,12,0,tzinfo=zone)))
    def command(c,**kw):
        calls.append(c)
        if c.endswith(' FILL'):return f'201 MIXER OK\r\n{position[0]} 0.896296 {position[1]} 0.085185\r\n'
    monkeypatch.setattr(playout,'STATUS',{'ready':True});monkeypatch.setattr(playout,'command',command)
    monkeypatch.setattr('skycam.native_ticker.time.monotonic',lambda:clock[0])
    b=Broadcast(tmp_path);t=NativeTicker(tmp_path,b);t.tick();calls.clear()
    clock[0]=1000;t.tick()
    assert calls==['MIXER 1-22 FILL']  # 900 wall seconds cannot start an overlapping strip.
    position[0]=.4;calls.clear();t.tick()
    fill=next(c for c in calls if c.startswith('MIXER 1-23 FILL '))
    assert float(fill.split()[3])==pytest.approx(.4+.5+ITEM_GAP/3840)
    assert t.status['spacing_clock']=='mixer_position'

def test_loading_and_video_visibility_commit_on_same_frame(monkeypatch):
    from skycam import playout as p
    calls=[];monkeypatch.setattr(p,'command',calls.append);monkeypatch.setattr(p,'_slate_visible',{})
    p.source_picture('ntv-cam1',True)
    assert calls==['MIXER 9-1 OPACITY 0 DEFER','MIXER 9-10 OPACITY 1 DEFER','MIXER 9 COMMIT']
    assert p._slate_visible['ntv-cam1'] is False
    calls.clear();p.source_picture('ntv-cam1',False)
    assert calls==['MIXER 9-1 OPACITY 1 DEFER','MIXER 9-10 OPACITY 0 DEFER','MIXER 9 COMMIT']
    assert p._slate_visible['ntv-cam1'] is True
