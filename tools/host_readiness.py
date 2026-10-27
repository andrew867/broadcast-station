# SPDX-License-Identifier: Apache-2.0
"""Read-only Linux desktop readiness report. Does not start or change a station."""
import argparse
import json
import os
import platform
import re
import shutil
import stat
import subprocess
from pathlib import Path


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=12)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def drm_devices(root=Path('/sys/class/drm'), dev=Path('/dev/dri')):
    rows = []
    for path in sorted(root.glob('renderD*')):
        try:
            device = dev/path.name
            vendor = (path/'device/vendor').read_text().strip().lower()
            driver = (path/'device/driver').resolve().name
            info = device.stat()
            rows.append({'node': str(device), 'vendor_id': vendor, 'driver': driver,
                         'character_device': stat.S_ISCHR(info.st_mode), 'group_id': info.st_gid,
                         'current_user_read_write': os.access(device, os.R_OK | os.W_OK)})
        except OSError:
            rows.append({'node': str(dev/path.name), 'unavailable': True})
    return rows


def graphics_details(text):
    allowed = {'OpenGL vendor string': 'vendor', 'OpenGL renderer string': 'renderer',
               'OpenGL core profile version string': 'version'}
    result = {}
    for line in (text or '').splitlines():
        name, sep, value = line.strip().partition(':')
        if sep and name in allowed:
            result[allowed[name]] = value.strip()[:240]
    renderer = result.get('renderer', '').lower()
    result['software_renderer'] = any(x in renderer for x in ('llvmpipe', 'softpipe', 'software rasterizer')) if renderer else None
    return result


def inspect(gpu='intel'):
    checks = []
    def check(name, ok, detail):
        checks.append({'check': name, 'status': 'ready' if ok else 'blocked', 'detail': detail})
    linux = platform.system() == 'Linux'
    check('operating_system', linux, 'Full playout requires Linux; offline preview is separate.')
    check('architecture', platform.machine() in ('x86_64', 'AMD64'), 'The packaged runtime targets x86_64.')
    dependencies = {name: bool(shutil.which(name)) for name in ('docker', 'xauth', 'ffmpeg', 'ffprobe', 'glxinfo')}
    for name in ('docker', 'xauth'):
        check(name, dependencies[name], 'Install '+name+' before launch.')
    docker_ok = dependencies['docker'] and command(['docker', 'info', '--format', '{{.ServerVersion}}']) is not None
    compose_ok = dependencies['docker'] and command(['docker', 'compose', 'version', '--short']) is not None
    check('docker_access', docker_ok, 'The current user must be able to use the Docker daemon.')
    check('compose', compose_ok, 'Docker Compose is required.')
    buildx_ok = dependencies['docker'] and command(['docker', 'buildx', 'version']) is not None
    check('buildx', buildx_ok, 'Docker Buildx is required for source builds; install the Docker buildx plugin.')
    display = os.environ.get('DISPLAY', '')
    display_ok = bool(re.fullmatch(r':\d+(?:\.\d+)?', display))
    check('desktop_display', display_ok, 'Run from a terminal in the logged-in desktop session.')
    auth = Path(os.environ.get('XAUTHORITY', '/nonexistent'))
    check('display_auth_file', auth.is_file() and os.access(auth, os.R_OK),
          'XAUTHORITY must name a readable desktop cookie file. Cookie contents are never collected.')
    devices = drm_devices() if linux else []
    if gpu == 'intel':
        intel = [x for x in devices if x.get('vendor_id') == '0x8086' and x.get('character_device')]
        check('intel_render_node', bool(intel), 'An Intel DRM render device is required for this profile.')
        check('intel_profile_device', any(Path(x['node']).name == 'renderD128' for x in intel),
              'The current Intel Compose profile expects the Intel GPU at /dev/dri/renderD128.')
    else:
        check('nvidia_driver', command(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader']) is not None,
              'NVIDIA driver access is required; container GPU access still needs a runtime test.')
    graphics = graphics_details(command(['glxinfo', '-B']) if dependencies['glxinfo'] and display_ok else None)
    if graphics.get('software_renderer') is True:
        check('desktop_opengl', False, 'Desktop OpenGL is using a software renderer.')
    elif graphics.get('renderer'):
        check('desktop_opengl', True, 'Hardware desktop renderer observed; this does not qualify container OpenGL.')
    else:
        checks.append({'check': 'desktop_opengl', 'status': 'unverified',
                       'detail': 'No OpenGL renderer evidence. Install glxinfo and run in the desktop session.'})
    pulse = Path(os.environ.get('XDG_RUNTIME_DIR', '/nonexistent'))/'pulse/native'
    try:
        info = pulse.stat()
        audio = stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid()
    except (OSError, AttributeError):
        audio = False
    return {'schema_version': 1, 'gpu_profile': gpu, 'system': platform.system(),
            'architecture': platform.machine(), 'checks': checks, 'drm_devices': devices,
            'graphics': graphics, 'desktop_audio_socket': audio, 'recording_tools': {
                name: dependencies[name] for name in ('ffmpeg', 'ffprobe')},
            'blockers': sum(c['status'] == 'blocked' for c in checks),
            'scope': 'Read-only prerequisites, not hardware qualification. No containers started, images pulled, settings changed, network throughput tests, raw logs, hostnames, credentials or display cookies collected.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu', choices=['intel', 'nvidia'], default='intel')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = inspect(args.gpu)
    text = json.dumps(report, indent=2)+'\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(text)
    else:
        print(text, end='')
    return 2 if report['blockers'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
