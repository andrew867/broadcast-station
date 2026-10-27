import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from skycam.station_config import StationConfig
from tools import stationctl
from tools.station_config import engine_config
from tools.install_headless_startup import unit
from tools.install_runtime_services import units


def test_headless_rejects_desktop_consumers():
    for output in ({'hdmi':True},{'desktop_audio':True}):
        with pytest.raises(ValueError,match='Headless'):StationConfig(output={'headless':True,**output})
    assert not StationConfig().output.headless


def test_headless_graphics_uses_vulkan_without_debug_listener():
    config=StationConfig(output={'headless':True})
    root=ET.fromstring(engine_config(config,Path(__file__).parents[1]/'deploy/casparcg.config'))
    assert root.findtext('html/angle-backend')=='vulkan'
    assert root.findtext('html/remote-debugging-port')=='0'
    assert not root.findall('.//consumers/screen') and not root.findall('.//consumers/system-audio')


def test_headless_preflight_needs_no_session_or_xauth(tmp_path,monkeypatch):
    home=stationctl.prepare(tmp_path/'station')
    data=json.loads((home/'station.json').read_text());data['output'].update(headless=True,playout=True)
    (home/'station.json').write_text(json.dumps(data))
    monkeypatch.delenv('DISPLAY',raising=False);monkeypatch.delenv('XAUTHORITY',raising=False)
    monkeypatch.setattr(stationctl.platform,'system',lambda:'Linux')
    monkeypatch.setattr(stationctl.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(stationctl.shutil,'which',lambda tool:'/usr/bin/docker' if tool=='docker' else None)
    monkeypatch.setattr(stationctl.subprocess,'run',lambda *a,**k:type('R',(),{'returncode':0})())
    monkeypatch.setattr(stationctl.shutil,'disk_usage',lambda *a:type('R',(),{'free':10*1024**3})())
    assert stationctl.preflight(home,'nvidia')[0]==[]
    data['output']['hdmi']=True;(home/'station.json').write_text(json.dumps(data))
    assert any('HDMI' in e for e in stationctl.preflight(home,'nvidia')[0])


def test_headless_resume_does_not_create_cookie_or_desktop_mount(tmp_path,monkeypatch):
    home=stationctl.prepare(tmp_path/'station');d=json.loads((home/'station.json').read_text());d['output']['headless']=True;(home/'station.json').write_text(json.dumps(d))
    (home/'compose.env').write_text('DISPLAY=:1\nSTATION_XAUTHORITY=/old/cookie\n')
    calls=[]
    monkeypatch.setattr(stationctl.sys,'argv',['stationctl','resume',str(home)])
    monkeypatch.setattr(stationctl,'preflight',lambda *a:([],'',None))
    monkeypatch.setattr(stationctl,'prepare_xauthority',lambda *a:pytest.fail('Headless must not read desktop authentication'))
    monkeypatch.setattr(stationctl.os,'getuid',lambda:1000,raising=False);monkeypatch.setattr(stationctl.os,'getgid',lambda:1000,raising=False)
    monkeypatch.setattr(stationctl.subprocess,'run',lambda args,**kw:calls.append(args))
    stationctl.main()
    env=(home/'compose.env').read_text()
    assert 'STATION_HEADLESS=1' in env and 'DISPLAY=' not in env and 'XAUTHORITY=' not in env
    assert all(not any('compose.desktop.yaml' in a for a in cmd) for cmd in calls)
    assert any('compose.headless.yaml' in a for a in calls[-1])


def test_headless_services_survive_graphical_session_lifetime():
    name,body=unit(Path('/home/operator/station'),'intel')
    assert name.endswith('-headless.service') and 'WantedBy=default.target' in body
    assert 'graphical-session' not in body and 'session_start.py' in body
    watchdog=next(iter(units(Path('/home/operator/station'),'intel','rtmp://192.0.2.10/program',headless=True).values()))
    assert 'WantedBy=default.target' in watchdog and 'graphical-session' not in watchdog
    with pytest.raises(ValueError):units(Path('/home/operator/station'),'intel','rtmp://192.0.2.10/program',display=True,headless=True)
