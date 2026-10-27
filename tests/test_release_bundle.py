import hashlib
import json
import subprocess
import pytest
from tools.verify_bundle import verify, load_images


def fixture(tmp_path):
    assets = []
    images = {}
    for role in ('controller', 'engine'):
        name = role + '.tar.gz'
        payload = role.encode()
        (tmp_path / name).write_bytes(payload)
        assets.append({'name': name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        images[role] = {'asset': name, 'tag': 'station-' + role + ':0.1.0-alpha.1', 'id': 'sha256:' + 'a' * 64}
    data = {'schema': 1, 'version': '0.1.0-alpha.1', 'assets': assets, 'images': images}
    (tmp_path / 'release.json').write_text(json.dumps(data))
    return data


def test_valid_bundle(tmp_path):
    assert verify_after_write(tmp_path, fixture(tmp_path))['version'] == '0.1.0-alpha.1'


def verify_after_write(path, data):
    (path / 'release.json').write_text(json.dumps(data))
    return verify(path)


@pytest.mark.parametrize('mutation', ['traversal', 'duplicate', 'missing', 'digest', 'tag', 'identity'])
def test_reject_invalid_bundle(tmp_path, mutation):
    data = fixture(tmp_path)
    if mutation == 'traversal': data['assets'][0]['name'] = '../controller.tar.gz'
    if mutation == 'duplicate': data['assets'].append(dict(data['assets'][0]))
    if mutation == 'missing': (tmp_path / 'engine.tar.gz').unlink()
    if mutation == 'digest': (tmp_path / 'engine.tar.gz').write_bytes(b'broken')
    if mutation == 'tag': data['images']['engine']['tag'] = 'station-engine:latest'
    if mutation == 'identity': data['images']['engine']['id'] = 'unverified'
    with pytest.raises(ValueError): verify_after_write(tmp_path, data)


def test_docker_identity_is_verified(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    calls = []
    monkeypatch.setattr('tools.verify_bundle.subprocess.run', lambda args, **kwargs: calls.append(args))
    monkeypatch.setattr('tools.verify_bundle.subprocess.check_output', lambda *args, **kwargs: 'sha256:' + 'b' * 64)
    with pytest.raises(ValueError, match='Loaded image identity'):
        load_images(tmp_path, data)
    assert len(calls) == 1


def test_matching_identity_does_not_hide_unpack_failure(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if args[1] == 'run':
            raise subprocess.CalledProcessError(125, args, stderr='failed to convert whiteout')
    monkeypatch.setattr('tools.verify_bundle.subprocess.run', run)
    monkeypatch.setattr('tools.verify_bundle.subprocess.check_output', lambda *args, **kwargs: 'sha256:' + 'a' * 64)
    with pytest.raises(subprocess.CalledProcessError):
        load_images(tmp_path, data)
    assert len(calls) == 2
    assert calls[-1][-1] == data['images']['controller']['id']


def test_both_images_must_start_without_station_or_network(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    calls = []
    monkeypatch.setattr('tools.verify_bundle.subprocess.run', lambda args, **kwargs: calls.append(args))
    monkeypatch.setattr('tools.verify_bundle.subprocess.check_output', lambda *args, **kwargs: 'sha256:' + 'a' * 64)
    load_images(tmp_path, data)
    probes = [args for args in calls if args[1] == 'run']
    assert len(probes) == 2
    for probe in probes:
        assert probe[probe.index('--network') + 1] == 'none'
        assert probe[probe.index('--entrypoint') + 1] == '/bin/true'
        assert '--read-only' in probe and '--rm' in probe
