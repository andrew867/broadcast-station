import importlib.util,json,os,time
from pathlib import Path
import pytest
from tools.storage_maintenance import maintain
from tools.stationctl import prepare
from skycam.sources import CameraCatalog

def test_prepare_preserves_existing_station_and_no_private_camera_seed(tmp_path):
    home=prepare(tmp_path/'station')
    assert not (home/'data/broadcast/cameras.json').exists()
    catalog=CameraCatalog(home/'data')
    assert all(not c['enabled'] for c in catalog.cameras.values())
    original=b'{"operator":"kept"}'
    (home/'station.json').write_bytes(original)
    prepare(home)
    assert (home/'station.json').read_bytes()==original
    assert (home/'secrets').is_dir()

def test_intel_init_selects_hd_software_encoder_without_enabling_outputs(tmp_path):
    home=prepare(tmp_path/'intel',gpu='intel')
    config=json.loads((home/'station.json').read_text())
    assert config['output']['profile']=='1080p3000'
    assert config['output']['encoder']=='libx264' and config['output']['bitrate_kbps']==8000
    assert not any(config['providers'].values())
    assert not any(config['output'][k] for k in ('playout','publish','hdmi','desktop_audio'))
    original=(home/'station.json').read_bytes()
    prepare(home,gpu='nvidia')
    assert (home/'station.json').read_bytes()==original

def test_storage_only_removes_expendable_old_files(tmp_path):
    now=time.time()
    for name in ['map/tile-8-1-2.png','map/tile-8-1-3.png','broadcast/music.json','references/picture.jpg','api/accounting.sqlite','picture-history/camera/frame.jpg','radar-history/east/frame.jpg']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'x'*100)
        os.utime(path,(now-1000,now-1000))
    fresh=tmp_path/'map/tile-8-1-4.png';fresh.write_bytes(b'x'*100)
    result=maintain(tmp_path,100,30,0,now)
    assert result['files_removed']==2
    assert fresh.exists()
    assert (tmp_path/'broadcast/music.json').exists()
    assert (tmp_path/'references/picture.jpg').exists()
    assert (tmp_path/'api/accounting.sqlite').exists()
    assert (tmp_path/'picture-history/camera/frame.jpg').exists()
    assert (tmp_path/'radar-history/east/frame.jpg').exists()

def test_storage_does_not_follow_symlinks(tmp_path):
    outside=tmp_path/'keep';outside.mkdir();picture=outside/'tile-8-1-2.png';picture.write_bytes(b'x')
    data=tmp_path/'data';data.mkdir()
    try:(data/'map').symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('Symlink creation unavailable')
    maintain(data,0,1,0,time.time()+100000)
    assert picture.exists()

def test_camera_hub_uses_configured_upstream_and_tcp():
    path=Path(__file__).parents[1]/'deploy/camera-hub.py'
    spec=importlib.util.spec_from_file_location('station_camera_hub',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    result=mod.configuration([{'enabled':True,'media_path':'cam1'},{'enabled':False,'media_path':'cam2'}])
    assert set(result['paths'])=={'cam1'}
    assert result['paths']['cam1']['source']==mod.CONFIG.inputs.camera_base+'/cam1'
    assert result['paths']['cam1']['rtspTransport']=='tcp'
    assert not result['api'] and result['rtspTransports']==['tcp']

def test_camera_hub_coalesces_rapid_edits_without_losing_last_registry(tmp_path):
    path=Path(__file__).parents[1]/'deploy/camera-hub.py'
    spec=importlib.util.spec_from_file_location('hub_reload',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    target=tmp_path/'mediamtx.json'
    last=mod.write_configuration(target,'{"paths":{"cam1":{}}}',float('-inf'),100)
    last=mod.write_configuration(target,'{"paths":{"cam1":{},"cam2":{}}}',last,101)
    assert list(json.loads(target.read_text())['paths'])==['cam1']
    latest='{"paths":{"cam1":{},"cam2":{},"cam3":{}}}'
    last=mod.write_configuration(target,latest,last,102)
    assert json.loads(target.read_text())==json.loads(latest)
    assert mod.write_configuration(target,latest,last,105)==102
