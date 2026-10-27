from fastapi.testclient import TestClient
from skycam.app import app

def test_studio_pages_preserve_all_control_ids_and_no_writes():
    with TestClient(app) as client:
        original=client.get('/api/broadcast').json()['state']
        for page in ['live','rundown','graphics','music','news','system','setup']:
            response=client.get('/studio/'+page)
            assert response.status_code==200
            for control in ['takeCamera','saveRundown','saveMusic','headline','preview']:
                assert response.text.count('id="'+control+'"')==1
            assert '/static/studio-navigation.js' in response.text
        assert client.get('/api/broadcast').json()['state']==original
