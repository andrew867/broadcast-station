import json
import pytest
from skycam.rundown_library import RundownLibrary,LibraryWrite,LibraryConflict

def body(name='Evening',revision=0,camera='cam1'):
    return LibraryWrite(name=name,expected_revision=revision,config={'cues':[{'camera':camera,'seconds':25}],'resume_after_restart':True})

def test_roundtrip_rename_duplicate_and_export_do_not_touch_live_rundown(tmp_path):
    live=tmp_path/'broadcast/rundown.json';live.parent.mkdir();live.write_text('operator-owned')
    library=RundownLibrary(tmp_path);one=library.save(body());id=one['saved_id']
    library.save(body('Late evening',1),id)
    library.save(body('Copy',2))
    loaded=RundownLibrary(tmp_path)
    assert len(loaded.public()['items'])==2
    assert loaded.export(id)['name']=='Late evening'
    assert loaded.export(id)['config']['resume_after_restart'] is True
    assert live.read_text()=='operator-owned'

def test_revision_conflict_and_duplicate_name_preserve_disk(tmp_path):
    l=RundownLibrary(tmp_path);l.save(body());before=l.path.read_bytes()
    with pytest.raises(LibraryConflict):l.save(body('Other',0))
    with pytest.raises(ValueError,match='already used'):l.save(body('EVENING',1))
    assert l.path.read_bytes()==before

def test_delete_and_undo_are_persistent_and_revision_never_rewinds(tmp_path):
    l=RundownLibrary(tmp_path);id=l.save(body())['saved_id'];l.delete(id,1)
    assert not l.public()['items']
    l=RundownLibrary(tmp_path);l.undo(2)
    assert l.public()['revision']==3 and l.public()['items'][0]['id']==id
    l.undo(3);assert not l.public()['items']
    with pytest.raises(ValueError,match='No library change'):l.undo(4)

def test_invalid_data_and_corruption_never_overwrite_library(tmp_path):
    with pytest.raises(ValueError):body('  ')
    with pytest.raises(ValueError):body('one\ntwo')
    l=RundownLibrary(tmp_path);l.path.parent.mkdir();l.path.write_text('{broken')
    l=RundownLibrary(tmp_path)
    with pytest.raises(RuntimeError):l.save(body())
    assert l.path.read_text()=='{broken'

def test_history_is_bounded_and_export_import_validates_config(tmp_path):
    l=RundownLibrary(tmp_path);id=l.save(body())['saved_id']
    for i in range(1,25):l.save(body('Name '+str(i),i),id)
    assert len(l.document.history)==20
    exported=l.export(id)
    imported=LibraryWrite(name='Imported',config=exported['config'],expected_revision=25)
    l.save(imported)
    with pytest.raises(ValueError):LibraryWrite(name='bad',config={'cues':[{'camera':'../../file','seconds':1}]},expected_revision=26)
def test_api_guards_conflicts_and_export_without_live_changes(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    from skycam.rundown_library import RundownLibrary
    monkeypatch.setattr(module,'rundown_library',RundownLibrary(tmp_path))
    client=TestClient(module.app);headers={'X-Skycam-Edit':'1'}
    before=module.rundown.config.model_dump()
    body={'name':'Evening','expected_revision':0,'config':{'cues':[{'camera':'weather','seconds':25,'scene':'standard'}],'transition':'dissolve','resume_after_restart':True}}
    assert client.post('/api/rundown-library',json=body).status_code==403
    response=client.post('/api/rundown-library',json=body,headers=headers)
    assert response.status_code==200
    saved=response.json();key=saved['saved_id']
    assert client.post('/api/rundown-library',json=body,headers=headers).status_code==409
    exported=client.get(f'/api/rundown-library/{key}/export').json()
    assert exported['config']==body['config'] and exported['format']=='skycam-rundown'
    body['expected_revision']=1;body['name']='Bad';body['config']['cues'][0]['camera']='missing-view'
    assert client.post('/api/rundown-library',json=body,headers=headers).status_code==422
    assert client.request('DELETE',f'/api/rundown-library/{key}',json={'expected_revision':1},headers=headers).status_code==200
    restored=client.post('/api/rundown-library/undo',json={'expected_revision':2},headers=headers).json()
    assert restored['items'][0]['id']==key and module.rundown.config.model_dump()==before
