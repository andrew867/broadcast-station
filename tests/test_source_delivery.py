import importlib.util
import io
import tarfile
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from skycam.source_delivery import router


def packager():
    path=Path(__file__).resolve().parents[1]/'tools/package_source.py'
    spec=importlib.util.spec_from_file_location('package_source',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.package


def test_source_package_is_repeatable_and_excludes_runtime(tmp_path):
    root=tmp_path/'input';root.mkdir()
    (root/'main.py').write_text('print(1)')
    (root/'data').mkdir();(root/'data/private.json').write_text('private')
    (root/'output').mkdir();(root/'output/report.json').write_text('generated')
    (root/'.playwright-cli').mkdir();(root/'.playwright-cli'/'console.log').write_text('generated')
    one,two=tmp_path/'one.gz',tmp_path/'two.gz'
    assert packager()(root,one)==1
    packager()(root,two)
    assert one.read_bytes()==two.read_bytes()
    with tarfile.open(one) as tar:assert tar.getnames()==['station-source/main.py']
    (root/'accidental.key').write_text('fake')
    with pytest.raises(ValueError):packager()(root,two)


def test_source_download_uses_only_configured_immutable_archive(tmp_path,monkeypatch):
    path=tmp_path/'source.tar.gz'
    monkeypatch.setenv('STATION_SOURCE_ARCHIVE',str(path))
    app=FastAPI();app.include_router(router)
    client=TestClient(app)
    assert client.get('/source').status_code==503
    path.write_bytes(b'packaged source')
    response=client.get('/source?path=/etc/passwd')
    assert response.status_code==200 and response.content==b'packaged source'
    assert 'station-source.tar.gz' in response.headers['content-disposition']
