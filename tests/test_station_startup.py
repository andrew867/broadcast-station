import json,shlex
from pathlib import Path
from tools import session_start
from tools.stationctl import compose,prepare
from tools.install_autostart import entry,quote_exec
from tools.station_watchdog import host_ports


def test_desktop_exec_paths_round_trip_without_shell_expansion():
    values=['/home/test user/station', '/home/100%/station', '/home/a"b`c$d\\e']
    for value in values:
        # Desktop Entry general-string decoding, then quoted Exec argument decoding.
        encoded=quote_exec(value).replace('\\\\','\\')
        decoded=encoded[1:-1]
        for char in ('"','`','$','\\'):decoded=decoded.replace('\\'+char,char)
        assert decoded.replace('%%','%')==value
    text=entry(Path('/home/test user/station'),'intel',python='/usr/bin/python3')
    assert 'Terminal=false' in text and '--gpu' in text and 'intel' in text


def test_desktop_resume_respects_maintenance(tmp_path,monkeypatch):
    home=prepare(tmp_path/'station');(home/'runtime/maintenance').touch()
    monkeypatch.setattr(session_start,'preflight',lambda *a: (_ for _ in ()).throw(AssertionError('Must not launch')))
    assert session_start.resume(home,'nvidia')==0
    assert json.loads((home/'runtime/login-start.json').read_text())['state']=='maintenance'


def test_desktop_resume_waits_then_fails_without_building(tmp_path,monkeypatch):
    home=prepare(tmp_path/'station')
    monkeypatch.setattr(session_start,'preflight',lambda *a: (['Display unavailable'],'',None))
    assert session_start.resume(home,'nvidia',timeout=0)==1
    assert json.loads((home/'runtime/login-start.json').read_text())['state']=='failed'


def test_maintenance_enabled_during_preflight_cancels_pending_resume(tmp_path,monkeypatch):
    home=prepare(tmp_path/'station')
    def preflight(*args):
        (home/'runtime/maintenance').touch()
        return [],':0',None
    monkeypatch.setattr(session_start,'preflight',preflight)
    monkeypatch.setattr(session_start.subprocess,'run',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Must not launch')))
    assert session_start.resume(home,'nvidia')==0
    assert json.loads((home/'runtime/login-start.json').read_text())['state']=='maintenance'


def test_desktop_resume_invokes_only_prebuilt_resume(tmp_path,monkeypatch):
    home=prepare(tmp_path/'station');calls=[]
    monkeypatch.setattr(session_start,'preflight',lambda *a: ([],':0',None))
    def run(command,**kwargs):
        calls.append(command)
        return type('Result',(),{'returncode':0})()
    monkeypatch.setattr(session_start.subprocess,'run',run)
    assert session_start.resume(home,'intel')==0
    assert calls[0][-4:]==['resume',str(home),'--gpu','intel']
    assert json.loads((home/'runtime/login-start.json').read_text())['state']=='started'


def test_compose_audio_opt_in_and_watchdog_ports(tmp_path):
    home=prepare(tmp_path/'station')
    (home/'compose.env').write_text('STATION_HTTP_PORT=8877\nSTATION_AMCP_PORT=5353\n')
    assert not any('compose.audio' in arg for arg in compose(home,'nvidia'))
    assert host_ports(home)==(5353,8877)
    with (home/'compose.env').open('a') as f:f.write('STATION_DESKTOP_AUDIO=1\n')
    assert any('compose.audio' in arg for arg in compose(home,'nvidia'))


def test_one_watchdog_per_station_and_lock_released_on_close(tmp_path):
    import sys,pytest
    from tools.station_watchdog import acquire_lock
    if sys.platform!='linux':pytest.skip('Linux advisory lock integration')
    first=acquire_lock(tmp_path)
    try:
        with pytest.raises(RuntimeError,match='already watching'):acquire_lock(tmp_path)
    finally:first.close()
    second=acquire_lock(tmp_path);second.close()


def test_display_cookie_is_private_scoped_and_does_not_modify_original(tmp_path,monkeypatch):
    from tools import stationctl
    home=prepare(tmp_path/'station');source=tmp_path/'desktop-auth';source.write_bytes(b'original cookie')
    calls=[]
    def run(command,**kwargs):
        calls.append((command,kwargs))
        if 'nlist' in command:return type('R',(),{'returncode':0,'stdout':'0100 0004 686f7374 0001 30 0000 0000\n'})()
        assert kwargs['input'].startswith('ffff ')
        Path(command[2]).write_bytes(b'private auth')
        return type('R',(),{'returncode':0})()
    monkeypatch.setattr(stationctl.subprocess,'run',run)
    target=stationctl.prepare_xauthority(home,':1',source)
    assert target.read_bytes()==b'private auth' and source.read_bytes()==b'original cookie'
    assert calls[0][0][-2:]==['nlist',':1']
    assert len(list(home.glob('display-auth-*')))==0


def test_missing_display_cookie_fails_before_launch(tmp_path,monkeypatch):
    from tools import stationctl
    import pytest
    home=prepare(tmp_path/'station')
    monkeypatch.setattr(stationctl.subprocess,'run',lambda *a,**k:type('R',(),{'returncode':0,'stdout':''})())
    with pytest.raises(RuntimeError,match='No usable cookie'):stationctl.prepare_xauthority(home,':0',home/'missing')
    assert not (home/'display.xauthority').exists()


def test_restart_applies_configuration_without_rebuilding(tmp_path,monkeypatch):
    from tools import stationctl
    home=prepare(tmp_path/'station');auth=home/'display.xauthority';auth.touch();calls=[]
    monkeypatch.setattr(stationctl.sys,'argv',['stationctl','restart',str(home)])
    monkeypatch.setattr(stationctl,'preflight',lambda *a:([],':1',auth))
    monkeypatch.setattr(stationctl,'prepare_xauthority',lambda *a:auth)
    monkeypatch.setattr(stationctl.os,'getuid',lambda:1000,raising=False)
    monkeypatch.setattr(stationctl.os,'getgid',lambda:1000,raising=False)
    monkeypatch.setattr(stationctl.subprocess,'run',lambda args,**kw:calls.append(args))
    stationctl.main()
    assert not any('build' in call for call in calls)
    assert any('validate' in call and 'never' in call for call in calls)
    assert '--force-recreate' in calls[-1] and 'up' in calls[-1]
