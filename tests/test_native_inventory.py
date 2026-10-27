import io
import tarfile
from tools.native_inventory import collect


def test_inventory_reports_missing_files_and_retains_source_versions(tmp_path):
    notice=tmp_path/'usr/share/doc/example/copyright';notice.parent.mkdir(parents=True);notice.write_text('Notice')
    result=collect(tmp_path,'example\t1.2-3\tamd64\tsource-example\t1.2-1\n')
    package=result['os_packages'][0]
    assert package['source_package']=='source-example' and package['source_version']=='1.2-1'
    assert package['copyright']['present'] and len(package['copyright']['sha256'])==64
    assert result['missing_expected_files'] and not result['caspar_source_archive']['present']


def test_source_archive_is_inspected_without_extracting_and_ndi_is_reported(tmp_path):
    archive=tmp_path/'usr/share/station/caspar-source.tar.gz';archive.parent.mkdir(parents=True)
    with tarfile.open(archive,'w:gz') as tar:
        entry=tarfile.TarInfo('../unsafe.patch');entry.size=3;tar.addfile(entry,io.BytesIO(b'abc'))
    ndi=tmp_path/'usr/local/lib/libndi.so.6';ndi.parent.mkdir(parents=True);ndi.write_bytes(b'fixture')
    result=collect(tmp_path,'')
    assert result['caspar_source_archive']['patches']==['../unsafe.patch']
    assert result['ndi_runtime_matches']==['usr/local/lib/libndi.so.6']
    assert not (tmp_path.parent/'unsafe.patch').exists()
