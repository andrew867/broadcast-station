import pytest
from tools.collect_os_sources import packages
from tools.retain_cef_materials import retain
from tools import retain_cef_materials as cef


def test_source_identity_rejects_options_and_traversal():
    for name in ('--help','../source','name;command'):
        with pytest.raises(ValueError):packages({'os_packages':[{'source_package':name,'source_version':'1.0'}]})
    assert packages({'os_packages':[{'source_package':'libexample','source_version':'1:2.0-3'}]*2})==[('libexample','1:2.0-3')]


def test_cef_materials_require_runtime_identity(tmp_path):
    sdk=tmp_path/'sdk'
    for name in ('include','Release','libcef_dll','cmake'):(sdk/name).mkdir(parents=True)
    (sdk/'include/cef_version.h').write_text('142.0.17+g60aac24')
    (sdk/'Release/libcef.so').write_bytes(b'matching library')
    for name in ('CREDITS.html','LICENSE.txt','README.txt','CMakeLists.txt'):(sdk/name).write_text(name)
    runtime=tmp_path/'runtime.so';runtime.write_bytes(b'wrong library')
    with pytest.raises(ValueError,match='differs'):retain(tmp_path,tmp_path/'result',runtime)
    runtime.write_bytes(b'matching library')
    result=retain(tmp_path,tmp_path/'result',runtime)
    assert result['runtime_matches_sdk'] and (tmp_path/'result/sdk-wrapper-source.tar.gz').is_file()


def test_packaged_cef_requires_pinned_bytes_and_embedded_version(tmp_path,monkeypatch):
    sdk=tmp_path/'sdk'
    for name in ('include','Release','libcef_dll','cmake'):(sdk/name).mkdir(parents=True)
    (sdk/'include/cef_version.h').write_text('142.0.17+g60aac24')
    (sdk/'Release/libcef.so').write_bytes(b'sdk build')
    for name in ('CREDITS.html','LICENSE.txt','README.txt','CMakeLists.txt'):(sdk/name).write_text(name)
    runtime=tmp_path/'runtime.so';runtime.write_bytes(b'packaged build')
    monkeypatch.setattr(cef,'PACKAGED_RUNTIME_SHA256',cef.sha(runtime))
    monkeypatch.setattr(cef,'runtime_version',lambda path:[0]*8)
    with pytest.raises(ValueError,match='version'):retain(tmp_path,tmp_path/'result',runtime)
    monkeypatch.setattr(cef,'runtime_version',lambda path:[142,0,17,3316,142,0,7444,176])
    result=retain(tmp_path,tmp_path/'result',runtime)
    assert not result['runtime_matches_sdk']
    assert result['libcef_sha256']!=result['sdk_libcef_sha256']
