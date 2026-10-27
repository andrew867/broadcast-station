import hashlib,io,json,tarfile
from pathlib import Path
import pytest
from skycam.station_config import StationConfig,load
from tools.import_station import import_snapshot
from tools.station_config import engine_config


def archive(tmp_path,extra=None):
    files={'data-web/broadcast/cameras.json':json.dumps({'version':1,'cameras':[{'id':'cam1','enabled':False}],'quads':{}}).encode(),
           'data-web/broadcast/music.json':b'{"volume":0.18,"source":"generated"}',
           'casparcg.config':b'<configuration><channels><channel><video-mode>2160p3000</video-mode></channel></channels></configuration>'}
    files.update(extra or {})
    files['manifest.json']=json.dumps({k:hashlib.sha256(v).hexdigest() for k,v in files.items()}).encode()
    path=tmp_path/'snapshot.tgz'
    with tarfile.open(path,'w:gz') as tar:
        for name,data in files.items():
            m=tarfile.TarInfo(name);m.size=len(data);tar.addfile(m,io.BytesIO(data))
    return path


def test_config_rejects_versions_credentials_paths_and_timezone(tmp_path):
    for row in ({'schema_version':2},{'inputs':{'adsb_url':'https://user:pass@example.com'}},
                {'secrets':{'finnhub':'../key'}},{'location':{'timezone':'not/a/timezone'}},
                {'output':{'audio_rate':44100}},{'providers':{'invented':True}}):
        p=tmp_path/'station.json';p.write_text(json.dumps(row))
        with pytest.raises(ValueError) as error:load(p)
        assert 'password' not in str(error.value)


def test_defaults_have_no_live_provider_or_output():
    c=StationConfig()
    assert not any(c.providers.values()) and not c.output.playout and not c.output.publish
    assert c.location.timezone=='UTC' and c.location.latitude==0
    assert c.output.x264_preset=='veryfast'
    assert StationConfig(output={'encoder':'libx264','x264_preset':'superfast'}).output.x264_preset=='superfast'
    with pytest.raises(ValueError):StationConfig(output={'x264_preset':'invalid -ar:a 1'})


def test_import_preserves_bytes_and_refuses_overwrite(tmp_path):
    source=archive(tmp_path);before=source.read_bytes();dest=tmp_path/'new'
    report=import_snapshot(source,dest)
    assert report['disabled_cameras']==['cam1']
    assert (dest/'data/broadcast/music.json').read_bytes()==b'{"volume":0.18,"source":"generated"}'
    assert load(dest/'station.json').output.profile=='2160p3000'
    assert not load(dest/'station.json').output.playout and source.read_bytes()==before
    with pytest.raises(ValueError):import_snapshot(source,dest)


def test_import_preserves_paired_radar_models_and_images(tmp_path):
    assets=Path(__file__).parents[1]/'skycam/radar'
    dest=tmp_path/'with-radar'
    report=import_snapshot(archive(tmp_path),dest,radar_calibration=assets)
    assert report['radar_calibrations_copied']==['east','island']
    for kind in ('east','island'):
        for name in (kind+'.json',kind+'-reference.jpg'):
            assert (dest/'data/radar/calibration'/name).read_bytes()==(assets/name).read_bytes()
    missing=import_snapshot(archive(tmp_path),tmp_path/'dry',dry_run=True)
    assert {x['radar'] for x in missing['missing_assets'] if 'radar' in x}=={'east','island'}


def test_dry_run_and_unsafe_archive_never_write_destination(tmp_path):
    path=archive(tmp_path);dest=tmp_path/'new'
    assert import_snapshot(path,dest,dry_run=True)['offline_rehearsal'] and not dest.exists()
    path=archive(tmp_path,{'data-web/../../escape':b'no'})
    with pytest.raises(ValueError):import_snapshot(path,dest)
    assert not dest.exists() and not (tmp_path/'escape').exists()


def test_import_detects_tampered_manifest(tmp_path):
    path=archive(tmp_path,{'manifest.json':b'{}'})
    # archive() includes manifest.json in its own declared set in this case.
    with pytest.raises(ValueError):import_snapshot(path,tmp_path/'new')


def test_engine_profile_has_matching_channel_clock():
    import xml.etree.ElementTree as ET
    c=StationConfig(output={'profile':'1080p3000'})
    result=ET.fromstring(engine_config(c,Path(__file__).parents[1]/'deploy/casparcg.config'))
    modes=[x.text for x in result.findall('./channels/channel/video-mode')]
    assert modes[:3]==['1080p3000']*3 and all(x.endswith('3000') for x in modes)


def test_accounting_import_closes_database_before_atomic_rename(tmp_path):
    import sqlite3
    from contextlib import closing
    state=tmp_path/'old-accounting';state.mkdir()
    (state/'policy.json').write_text('{"enabled":false}')
    with closing(sqlite3.connect(state/'usage.sqlite')) as db:
        db.execute('CREATE TABLE spending(amount INTEGER)');db.execute('INSERT INTO spending VALUES (7)');db.commit()
    dest=tmp_path/'new'
    result=import_snapshot(archive(tmp_path),dest,aeroapi_state=state)
    assert result['accounting_preserved']
    with closing(sqlite3.connect(dest/'accounting/aeroapi/usage.sqlite')) as db:
        assert db.execute('SELECT amount FROM spending').fetchone()[0]==7


def test_desktop_audio_and_duplicate_logs_are_explicit():
    import xml.etree.ElementTree as ET
    template=Path(__file__).parents[1]/'deploy/casparcg.config'
    muted=ET.fromstring(engine_config(StationConfig(),template))
    assert not muted.findall('.//system-audio')
    audible=ET.fromstring(engine_config(StationConfig(output={'desktop_audio':True}),template))
    assert len(audible.findall('.//system-audio'))==1
    assert audible.find('./channels/channel/consumers/system-audio/delay').text=='200ms'
    assert audible.find('./paths/log-path').get('disabled')=='true'


def test_health_inputs_require_rtsp_and_rtmp_base_is_separate():
    with pytest.raises(ValueError):StationConfig(inputs={'camera_base':'rtmp://example.com/cam'})
    with pytest.raises(ValueError):StationConfig(inputs={'camera_rtmp_base':'rtsp://example.com/cam'})


def test_native_camera_policy_uses_configured_bases():
    import xml.etree.ElementTree as ET
    c=StationConfig(inputs={'camera_base':'rtsp://upstream:8554/live'})
    result=ET.fromstring(engine_config(c,Path(__file__).parents[1]/'deploy/casparcg.config'))
    prefixes=[n.text for n in result.findall('./ffmpeg/producer/camera-prefixes/prefix')]
    assert 'rtsp://upstream:8554/live/' in prefixes
    assert 'rtsp://source-hub:8554/' in prefixes
    assert len(prefixes)==len(set(prefixes)) and all(p.endswith('/') for p in prefixes)
