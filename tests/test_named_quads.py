import pytest
from skycam.sources import CameraCatalog,QuadSpec,CameraSpec


def spec(id='quad-coast',name='Coastal views'):
    return QuadSpec(id=id,name=name,cameras=['cam4','ntv-cam4','cam3','cam1'])


def test_named_quads_survive_camera_edits_and_restart(tmp_path):
    catalog=CameraCatalog(tmp_path);before={k:v['channel'] for k,v in catalog.cameras.items()}
    catalog.write_quad(spec(),create=True)
    source=catalog.cameras['cam1']
    catalog.update('cam1',CameraSpec(**{k:v for k,v in source.items() if k in CameraSpec.model_fields}))
    restored=CameraCatalog(tmp_path)
    assert restored.quad_names['quad-coast']=='Coastal views'
    assert restored.quads['quad-coast']==spec().cameras
    assert before=={k:v['channel'] for k,v in restored.cameras.items()}
    restored.write_quad(spec(name='Bays and coastline'))
    assert CameraCatalog(tmp_path).quad_names['quad-coast']=='Bays and coastline'
    restored.delete_quad('quad-coast')
    assert 'quad-coast' not in CameraCatalog(tmp_path).quads
    with pytest.raises(ValueError):restored.write_quad(spec(),create=True)


def test_quad_capacity_duplicate_members_and_reserved_defaults(tmp_path):
    catalog=CameraCatalog(tmp_path)
    with pytest.raises(ValueError):catalog.write_quad(spec().model_copy(update={'cameras':['cam1']*4}),create=True)
    for i in range(10):catalog.write_quad(spec(id=f'quad-{i}'),create=True)
    with pytest.raises(ValueError,match='twelve'):catalog.write_quad(spec(),create=True)
    with pytest.raises(ValueError):catalog.delete_quad('quad')
    with pytest.raises(ValueError):catalog.create(CameraSpec(id='quad-1',name='Collision',media_path='collision'))
    snapshot=catalog.public();snapshot['quads']['quad'][0]='changed'
    assert catalog.quads['quad'][0]=='cam1'


def test_quad_api_authorization_and_referenced_scene_guards(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module,sources
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    from skycam.rundown import Rundown,RundownConfig
    from skycam.rundown_library import RundownLibrary,LibraryWrite
    catalog=CameraCatalog(tmp_path)
    for target in (module,sources):
        monkeypatch.setattr(target,'CATALOG',catalog)
        monkeypatch.setattr(target,'CAMERAS',catalog.cameras)
        monkeypatch.setattr(target,'QUADS',catalog.quads)
    rundown=Rundown(tmp_path,lambda *args:None)
    library=RundownLibrary(tmp_path)
    monkeypatch.setattr(module,'rundown',rundown);monkeypatch.setattr(module,'rundown_library',library)
    monkeypatch.setattr(module.playout,'ENABLED',False)
    monkeypatch.setattr(module.playout,'_prepared',None)
    client=TestClient(module.app);headers={'X-Skycam-Edit':'1'}
    assert client.post('/api/quad-scenes',json=spec().model_dump()).status_code==403
    assert client.post('/api/quad-scenes',json=spec().model_dump(),headers=headers).status_code==200
    assert any(row['id']=='quad-coast' for row in client.get('/api/scenes').json())
    assert client.patch('/api/quad-scenes/quad-coast',json=spec(name='Coast').model_dump(),headers=headers).status_code==200
    config=RundownConfig(cues=[{'camera':'quad-coast','seconds':30}])
    library.save(LibraryWrite(name='Coast',config=config,expected_revision=0))
    assert client.delete('/api/quad-scenes/quad-coast',headers=headers).status_code==409
    item=library.public()['items'][0];library.delete(item['id'],library.public()['revision'])
    monkeypatch.setattr(module.playout,'_prepared',{'camera':'quad-coast'})
    assert client.delete('/api/quad-scenes/quad-coast',headers=headers).status_code==409
    monkeypatch.setattr(module.playout,'_prepared',None)
    assert client.delete('/api/quad-scenes/quad-coast',headers=headers).status_code==200
