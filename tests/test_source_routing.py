import importlib.util
import json
from pathlib import Path
from skycam.source_routing import camera_base,DIRECT,SHARED

def test_shared_inputs_are_explicit_and_direct_is_rollback(tmp_path):
    assert camera_base(tmp_path)==DIRECT
    p=tmp_path/'broadcast/source-routing.json';p.parent.mkdir();p.write_text(json.dumps({'shared_camera_inputs':True}))
    assert camera_base(tmp_path)==SHARED
    p.write_text(json.dumps({'shared_camera_inputs':False}));assert camera_base(tmp_path)==DIRECT
    p.write_text('incomplete');assert camera_base(tmp_path)==DIRECT

def test_hub_is_container_internal_and_only_creates_enabled_known_paths():
    spec=importlib.util.spec_from_file_location('camera_hub',Path(__file__).parents[1]/'deploy/camera-hub.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    config=module.configuration([{'enabled':True,'media_path':'cam1'},{'enabled':False,'media_path':'cam2'},
                                {'enabled':True,'media_path':'bad?key=secret'}])
    assert config['rtspAddress']==':8554' and config['rtspTransports']==['tcp']
    assert all(not config[k] for k in ('api','rtmp','hls','moq','webrtc','srt','metrics','pprof','playback'))
    assert list(config['paths'])==['cam1'] and config['paths']['cam1']['sourceOnDemand']
