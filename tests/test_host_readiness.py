from tools import host_readiness as host


def test_renderer_report_excludes_host_and_detects_software():
    result=host.graphics_details('name of display: private-host:0\nOpenGL vendor string: Mesa\nOpenGL renderer string: llvmpipe (LLVM 19)\nOpenGL core profile version string: 4.5')
    assert result['software_renderer'] is True
    assert 'private-host' not in str(result)
    assert host.graphics_details('')['software_renderer'] is None


def test_missing_host_dependencies_are_reported_without_starting_anything(monkeypatch):
    calls=[]
    monkeypatch.setattr(host.platform,'system',lambda:'Linux')
    monkeypatch.setattr(host.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(host.shutil,'which',lambda name:None)
    monkeypatch.setattr(host,'drm_devices',lambda:[])
    monkeypatch.setattr(host,'command',lambda args:calls.append(args))
    monkeypatch.delenv('DISPLAY',raising=False)
    monkeypatch.delenv('XAUTHORITY',raising=False)
    result=host.inspect()
    assert result['blockers']>=5 and calls==[]
    assert not result['desktop_audio_socket']


def test_wrong_intel_device_number_is_not_silently_accepted(monkeypatch,tmp_path):
    monkeypatch.setattr(host.platform,'system',lambda:'Linux')
    monkeypatch.setattr(host.platform,'machine',lambda:'x86_64')
    monkeypatch.setattr(host.shutil,'which',lambda name:'/usr/bin/'+name)
    monkeypatch.setattr(host,'drm_devices',lambda:[{'node':'/dev/dri/renderD129','vendor_id':'0x8086','character_device':True}])
    calls=[]
    def run(args):
        calls.append(args)
        return 'OpenGL renderer string: Mesa Intel UHD 620' if args[0]=='glxinfo' else 'available'
    monkeypatch.setattr(host,'command',run)
    monkeypatch.setenv('DISPLAY',':0')
    auth=tmp_path/'auth';auth.write_text('PRIVATE COOKIE')
    monkeypatch.setenv('XAUTHORITY',str(auth))
    result=host.inspect()
    checks={c['check']:c['status'] for c in result['checks']}
    assert checks['intel_render_node']=='ready' and checks['intel_profile_device']=='blocked'
    assert 'PRIVATE COOKIE' not in str(result)
    assert all('run' not in c and 'pull' not in c for c in calls)
