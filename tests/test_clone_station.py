import hashlib
import io
import json
import tarfile

import pytest

from skycam.station_config import StationConfig, load
from tools.clone_station import clone


def snapshot(tmp_path, extra=None):
    config = StationConfig().model_dump(mode='json')
    config['output'].update(playout=True, publish=True, publish_url='rtmp://example.test/private')
    config['secrets'] = {'finnhub': 'finnhub.key'}
    config['providers']['news'] = True
    files = {
        'station.json': json.dumps(config).encode(),
        'compose.env': b'STATION_HOME=/original\n',
        'branding.json': b'{"name":"Test station"}',
        'data/broadcast/cameras.json': b'{"cameras":[{"id":"cam1","enabled":true},{"id":"cam2","enabled":true}],"quads":{}}',
        'data/broadcast/rundown.json': b'{"resume_after_restart":true,"items":[{"camera":"cam1"}]}',
        'data/broadcast/program-clock.json': b'{"config":{"enabled":true}}',
        'data/broadcast/state.json': b'{"camera":"cam2"}',
        'data/source-health.json': b'{"stale":true}',
        'data/references/cam1.png': b'example image',
        'accounting/aeroapi/policy.json': b'{"enabled":true}',
        'accounting/aeroapi/usage.sqlite': b'example ledger',
    }
    files.update(extra or {})
    files['manifest.json'] = json.dumps({k: hashlib.sha256(v).hexdigest() for k,v in files.items()}).encode()
    path = tmp_path/'snapshot.tgz'
    with tarfile.open(path,'w:gz') as archive:
        for name,data in files.items():
            member = tarfile.TarInfo(name); member.size = len(data)
            archive.addfile(member,io.BytesIO(data))
    return path,hashlib.sha256(path.read_bytes()).hexdigest()


def test_clone_is_inactive_and_preserves_settings_and_ledger(tmp_path):
    source,digest = snapshot(tmp_path); before = source.read_bytes(); dest = tmp_path/'standby'
    clone(source,dest,digest,['cam1'])
    config = load(dest/'station.json')
    assert not config.output.playout and not config.output.publish
    assert config.output.publish_url == '' and not config.secrets and not any(config.providers.values())
    assert config.output.profile == '1080p3000' and config.output.encoder == 'libx264'
    assert not (dest/'compose.env').exists() and not (dest/'data/source-health.json').exists()
    assert json.loads((dest/'data/broadcast/cameras.json').read_text())['cameras'][1]['enabled'] is False
    assert json.loads((dest/'standby-original/program-clock.json').read_text())['config']['enabled']
    assert not json.loads((dest/'data/broadcast/program-clock.json').read_text())['config']['enabled']
    assert not json.loads((dest/'data/broadcast/rundown.json').read_text())['resume_after_restart']
    assert (dest/'data/references/cam1.png').read_bytes() == b'example image'
    assert (dest/'accounting/aeroapi/usage.sqlite').read_bytes() == b'example ledger'
    assert not json.loads((dest/'accounting/aeroapi/policy.json').read_text())['enabled']
    assert source.read_bytes() == before
    with pytest.raises(ValueError): clone(source,dest,digest,['cam1'])


@pytest.mark.parametrize('extra', [{'data/../../escape':b'x'}, {'secrets/key.key':b'secret'}, {'data/key.txt':b'-----BEGIN '+b'PRIVATE KEY-----'}])
def test_rejects_unsafe_payloads_before_writing(tmp_path,extra):
    source,digest=snapshot(tmp_path,extra); dest=tmp_path/'standby'
    with pytest.raises(ValueError): clone(source,dest,digest,['cam1'])
    assert not dest.exists()


def test_hash_and_unknown_camera_guard(tmp_path):
    source,digest=snapshot(tmp_path); dest=tmp_path/'standby'
    with pytest.raises(ValueError): clone(source,dest,'0'*64,['cam1'])
    with pytest.raises(ValueError): clone(source,dest,digest,['missing'])
    assert not dest.exists()
