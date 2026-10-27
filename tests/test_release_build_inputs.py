import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def report():
    return {'environment':{'sys_platform':'linux','platform_machine':'x86_64','python_version':'3.13'},
            'install':[{'metadata':{'name':'example','version':'1.0'},
                        'download_info':{'url':'https://files.pythonhosted.org/example.whl',
                                         'archive_info':{'hashes':{'sha256':'a'*64}}}}]}


def test_linux_hash_lock_rejects_unreviewed_sources_and_platforms():
    render = module('lock_from_report').render
    value = report()
    assert 'example==1.0 --hash=sha256:'+'a'*64 in render(value)
    for url in ('http://files.pythonhosted.org/example.whl', 'https://example.org/example.whl',
                'https://files.pythonhosted.org/example.tar.gz', 'https://' + 'user:secret@files.pythonhosted.org/example.whl'):
        bad = copy.deepcopy(value)
        bad['install'][0]['download_info']['url'] = url
        with pytest.raises(ValueError):render(bad)
    bad = copy.deepcopy(value)
    bad['environment']['platform_machine'] = 'aarch64'
    with pytest.raises(ValueError):render(bad)
    bad = copy.deepcopy(value)
    bad['install'][0]['download_info']['archive_info']['hashes'] = {}
    with pytest.raises(ValueError):render(bad)


def test_test_lock_preserves_every_runtime_artifact():
    def entries(name):
        return {line for line in (ROOT/name).read_text(encoding='utf-8').splitlines() if line and not line.startswith('#')}
    runtime = entries('requirements-linux-x86_64.lock')
    test = entries('requirements-test-linux-x86_64.lock')
    assert runtime and runtime <= test


def test_music_source_archive_and_bundle_match_reviewed_hashes():
    assert module('verify_music_source').verify()['source_files'] == 83
