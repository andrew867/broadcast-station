import json
from types import SimpleNamespace
import pytest
from tools.install_runtime_services import monitor_url,units,quote
from tools import keep_display_awake as awake
from tools.stationctl import http_bind
from tools.stationctl import compose
from tools.station_watchdog import studio_host,controller_age


def test_controller_can_update_between_loop_start_and_http_response():
    # Loop started at 100; the controller updates during the probe. It is fresh.
    assert controller_age({'playout':{'checked_at':100.4}},100.8)==pytest.approx(.4)
    assert controller_age({'playout':{'checked_at':30}},100.8)>60
    assert controller_age({'playout':{'checked_at':110}},100.8)<0
    for bad in (None,True,'100',float('nan')):
        assert controller_age({'playout':{'checked_at':bad}},100.8) is None


@pytest.mark.parametrize('address',['0.0.0.0','8.8.8.8','::1','example.com','169.254.2.1'])
def test_studio_rejects_unspecified_public_and_link_local_bind(address):
    with pytest.raises(ValueError):http_bind(address)


def test_watchdog_probes_selected_private_interface(tmp_path):
    (tmp_path/'compose.env').write_text('STATION_HTTP_PORT=8765\nSTATION_HTTP_BIND=192.168.2.4\n')
    assert studio_host(tmp_path)=='192.168.2.4'
    (tmp_path/'compose.env').write_text('STATION_HTTP_PORT=8765\n')
    assert studio_host(tmp_path)=='127.0.0.1'


def test_hybrid_health_profile_is_explicit_and_persisted(tmp_path):
    (tmp_path/'compose.env').write_text('STATION_HTTP_PORT=8765\n')
    assert not any('health-vaapi' in part for part in compose(tmp_path,'nvidia'))
    (tmp_path/'compose.env').write_text('STATION_HEALTH_DEVICE=/dev/dri/renderD128\nSTATION_HEALTH_GID=109\n')
    command=compose(tmp_path,'nvidia')
    assert any('compose.nvidia.yaml' in part for part in command)
    assert any('compose.health-vaapi.yaml' in part for part in command)


def test_service_arguments_are_literal_and_station_scoped(tmp_path):
    home=tmp_path/'my station %name $HOME'
    rows=units(home,'intel','rtsp://relay:8554/program',True,python='/usr/bin/python3')
    assert len(rows)==2
    for name,body in rows.items():
        assert name.startswith('station-') and 'PartOf=graphical-session.target' in body
        assert '%%name $$HOME' in body and '--gpu" "intel' in body
        assert 'UMask=0077' in body
    assert list(rows)!=list(units(tmp_path/'other','intel','rtsp://relay:8554/program',True))
    with pytest.raises(ValueError):quote('bad\nargument')


@pytest.mark.parametrize('url',['https://user:pass@example.com','http://relay/?key=x','rtsp://relay/#secret','file:///etc/passwd','rtsp://relay/a\nb'])
def test_monitor_endpoint_cannot_put_a_secret_in_service(url):
    with pytest.raises(ValueError):monitor_url(url)


def test_inhibitor_tracks_correct_compose_engine_and_respects_maintenance(tmp_path,monkeypatch):
    (tmp_path/'runtime').mkdir();(tmp_path/'station.json').write_text(json.dumps({'output':{'hdmi':True}}))
    calls=[]
    monkeypatch.setattr(awake,'compose',lambda home,gpu:['docker','compose','-p','unique-station'])
    def run(args,**kwargs):calls.append(args);return SimpleNamespace(returncode=0,stdout='engine-id\n')
    monkeypatch.setattr(awake.subprocess,'run',run)
    assert awake.needs_inhibit(tmp_path,'nvidia')
    assert calls[-1][-5:]==['ps','--status','running','-q','engine']
    (tmp_path/'runtime/maintenance').touch()
    assert not awake.needs_inhibit(tmp_path,'nvidia') and len(calls)==1
    (tmp_path/'runtime/maintenance').unlink()
    (tmp_path/'station.json').write_text('{"output":{"hdmi":false}}')
    assert not awake.needs_inhibit(tmp_path,'nvidia') and len(calls)==1
