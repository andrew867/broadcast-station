# SPDX-License-Identifier: Apache-2.0
"""Prepare and launch an isolated station directory using only Python's standard library."""
import argparse,ipaddress,json,os,platform,re,shutil,socket,stat,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FOLDERS=['data','runtime','music','logs','engine-data','templates','secrets','branding-assets']


def http_bind(value):
    address=ipaddress.IPv4Address(value)
    private_ranges=[ipaddress.IPv4Network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8')]
    if not any(address in network for network in private_ranges):
        raise ValueError('Studio must bind a specific loopback or private LAN IPv4 address')
    return str(address)


def prepare(home,gpu='nvidia'):
    if gpu not in ('nvidia','intel'):raise ValueError('Unknown GPU profile')
    home=Path(home).resolve();home.mkdir(parents=True,exist_ok=True)
    for folder in FOLDERS:(home/folder).mkdir(exist_ok=True)
    if os.name!='nt':
        home.chmod(0o700);(home/'secrets').chmod(0o700)
    if not (home/'station.json').exists():
        config=json.loads((ROOT/'examples/station.json').read_text())
        config.update(data_directory='/workspace/data-web',music_directory='/workspace/media/music',brand_file='/station/branding.json',secrets_directory='/station/secrets')
        config['inputs']['camera_base']='rtsp://192.0.2.10:8554'
        if gpu=='intel':
            config['output'].update(profile='1080p3000',encoder='libx264',bitrate_kbps=8000)
        (home/'station.json').write_text(json.dumps(config,indent=2)+'\n')
    if not (home/'branding.json').exists():shutil.copyfile(ROOT/'examples/branding.json',home/'branding.json')
    broadcast=home/'data/broadcast';broadcast.mkdir(parents=True,exist_ok=True)
    if not (home/'casparcg.config').exists():shutil.copyfile(ROOT/'deploy/casparcg.config',home/'casparcg.config')
    if not (broadcast/'source-routing.json').exists():(broadcast/'source-routing.json').write_text('{"shared_camera_inputs":true}\n')
    # The controller creates disabled demonstration cameras, never live sources.
    return home


def preflight(home,gpu):
    errors=[];config=json.loads((home/'station.json').read_text())
    headless=config.get('output',{}).get('headless',False)
    if headless and (config.get('output',{}).get('hdmi') or config.get('output',{}).get('desktop_audio')):
        errors.append('Headless mode requires HDMI and desktop audio to be disabled')
    if platform.system()!='Linux':errors.append('Full playout requires Linux; offline preview works elsewhere')
    if platform.machine() not in ('x86_64','AMD64'):errors.append('This candidate targets x86_64')
    if not shutil.which('docker'):errors.append('Docker is missing')
    else:
        for args,label in [(['docker','info'],'Docker daemon'),(['docker','compose','version'],'Docker Compose')]:
            try:r=subprocess.run(args,capture_output=True,timeout=15);ok=r.returncode==0
            except (OSError,subprocess.TimeoutExpired):ok=False
            if not ok:errors.append(label+' is unavailable')
    display=os.environ.get('DISPLAY','');auth=Path(os.environ.get('XAUTHORITY','/nonexistent'))
    if not headless:
        if not re.fullmatch(r':\d+(?:\.\d+)?',display):errors.append('A local X11/Xwayland DISPLAY is required')
        if not shutil.which('xauth'):errors.append('Install xauth to prepare a private container display cookie')
        if not auth.is_file() or not os.access(auth,os.R_OK):errors.append('A readable XAUTHORITY file is required; run from the logged-in desktop session')
    if config.get('output',{}).get('desktop_audio'):
        pulse=Path(os.environ.get('XDG_RUNTIME_DIR','/nonexistent'))/'pulse/native'
        try:valid=stat.S_ISSOCK(pulse.stat().st_mode) and pulse.stat().st_uid==os.getuid()
        except OSError:valid=False
        if not valid:errors.append('Desktop audio requires your logged-in PulseAudio or PipeWire pulse socket')
    if gpu=='nvidia':
        try:r=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],capture_output=True,timeout=10);ok=r.returncode==0
        except (OSError,subprocess.TimeoutExpired):ok=False
        if not ok:errors.append('NVIDIA driver check failed')
    elif not Path('/dev/dri/renderD128').exists():errors.append('Intel render device is missing')
    if not config.get('output',{}).get('playout'):errors.append('Review station.json and enable output.playout before launching')
    if gpu=='intel' and config.get('output',{}).get('encoder','h264_nvenc')!='libx264':errors.append('Intel candidate requires encoder libx264; QSV is not qualified')
    if gpu=='intel' and config.get('output',{}).get('profile') not in ('720p3000','720p6000','1080p3000','1080i5994'):errors.append('Intel candidate supports HD profiles only; each workload still needs hardware acceptance')
    if shutil.disk_usage(home).free<5*1024**3:errors.append('Less than 5 GiB free space')
    return errors,display,auth


def prepare_xauthority(home,display,source):
    # A desktop cookie usually identifies the host, while the container has a
    # different hostname. Retain only this display's cookie, with FamilyWild.
    # It remains private and authenticated; no xhost or anonymous access.
    result=subprocess.run(['xauth','-f',str(source),'nlist',display],capture_output=True,text=True,timeout=10)
    records=result.stdout.splitlines()
    if result.returncode or not records or any(not re.fullmatch(r'[0-9a-fA-F ]+',row) or len(row)<8 for row in records):
        raise RuntimeError('No usable cookie for the current display; run from its logged-in session')
    fd,name=tempfile.mkstemp(prefix='display-auth-',dir=home);os.close(fd);temporary=Path(name)
    try:
        merged=subprocess.run(['xauth','-f',str(temporary),'nmerge','-'],input=''.join('ffff'+row[4:]+'\n' for row in records),capture_output=True,text=True,timeout=10)
        if merged.returncode or temporary.stat().st_size==0:raise RuntimeError('Could not prepare the private display cookie')
        temporary.chmod(0o600);target=home/'display.xauthority';temporary.replace(target)
        return target
    finally:temporary.unlink(missing_ok=True)


def compose(home,gpu):
    command=['docker','compose','--env-file',str(home/'compose.env'),'-f',str(ROOT/'compose.station.yaml'),'-f',str(ROOT/('compose.'+gpu+'.yaml'))]
    env=home/'compose.env'
    saved=dict(line.split('=',1) for line in env.read_text().splitlines() if '=' in line) if env.is_file() else {}
    command+=['-f',str(ROOT/('compose.headless.yaml' if saved.get('STATION_HEADLESS')=='1' else 'compose.desktop.yaml'))]
    if env.is_file() and 'STATION_DESKTOP_AUDIO=1' in env.read_text().splitlines():command+=['-f',str(ROOT/'compose.audio.yaml')]
    if env.is_file() and any(line.startswith('STATION_HEALTH_DEVICE=') for line in env.read_text().splitlines()):command+=['-f',str(ROOT/'compose.health-vaapi.yaml')]
    return command


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['init','prepare','check','start','restart','resume','stop','status','logs']);parser.add_argument('home',type=Path);parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');args=parser.parse_args()
    home=args.home.resolve()
    if args.action=='init' and (home/'station.json').exists():raise SystemExit('Station already exists; prepare preserves existing settings')
    if args.action in ('init','prepare'):
        prepare(home,args.gpu);print('Station folders prepared. Edit station.json and branding.json before start.');return
    if args.action in ('stop','status','logs'):
        action={'stop':['stop'],'status':['ps'],'logs':['logs','--tail','100']}[args.action]
        raise SystemExit(subprocess.call(compose(home,args.gpu)+action))
    errors,display,auth=preflight(home,args.gpu)
    if errors:raise SystemExit('\n'.join(errors))
    import hashlib
    headless=json.loads((home/'station.json').read_text()).get('output',{}).get('headless',False)
    values={'STATION_HOME':str(home),'STATION_UID':str(os.getuid()),'STATION_GID':str(os.getgid()),'STATION_HEADLESS':'1' if headless else '0','COMPOSE_PROJECT_NAME':'station-'+hashlib.sha256(str(home).encode()).hexdigest()[:10]}
    if not headless:
        container_auth=prepare_xauthority(home,display,auth)
        values.update(DISPLAY=display,STATION_XAUTHORITY=str(container_auth))
    saved=dict(line.split('=',1) for line in (home/'compose.env').read_text().splitlines() if '=' in line) if (home/'compose.env').is_file() else {}
    for key in ('STATION_CONTROLLER_IMAGE','STATION_ENGINE_IMAGE'):
        value=os.environ.get(key,saved.get(key,''))
        if value:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/@-]{0,255}',value):raise SystemExit('Invalid '+key)
            values[key]=value
    values['STATION_HTTP_BIND']=http_bind(os.environ.get('STATION_HTTP_BIND',saved.get('STATION_HTTP_BIND','127.0.0.1')))
    allowed_hosts=os.environ.get('STATION_ALLOWED_HOSTS',saved.get('STATION_ALLOWED_HOSTS',''))
    if allowed_hosts:
        names=[name.strip().lower() for name in allowed_hosts.split(',')]
        if any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?',name) for name in names):
            raise SystemExit('Invalid STATION_ALLOWED_HOSTS; use comma-separated host names without ports')
        values['STATION_ALLOWED_HOSTS']=','.join(names)
    health_device=os.environ.get('STATION_HEALTH_DEVICE',saved.get('STATION_HEALTH_DEVICE',''))
    if health_device:
        if not re.fullmatch(r'/dev/dri/renderD[0-9]+',health_device):raise SystemExit('Health decoder requires a DRM render device')
        device=Path(health_device)
        if not device.exists() or not stat.S_ISCHR(device.stat().st_mode):raise SystemExit('Health decoder render device is unavailable')
        values['STATION_HEALTH_DEVICE']=health_device
        values['STATION_HEALTH_GID']=str(device.stat().st_gid)
    for name,default in [('STATION_HTTP_PORT','8765'),('STATION_AMCP_PORT','5250')]:
        value=os.environ.get(name,saved.get(name,default))
        if not value.isdecimal() or not 1<=int(value)<=65535:raise SystemExit('Invalid '+name)
        values[name]=value
    if json.loads((home/'station.json').read_text()).get('output',{}).get('desktop_audio'):
        values['STATION_DESKTOP_AUDIO']='1'
        values['STATION_PULSE_SOCKET']=str(Path(os.environ['XDG_RUNTIME_DIR'])/'pulse/native')
    if args.gpu=='intel':
        values['STATION_RENDER_GID']=str(Path('/dev/dri/renderD128').stat().st_gid)
        values['STATION_EGL_PLATFORM']='surfaceless' if headless else 'x11'
    if any(any(c in v for c in '\r\n$"\'') for v in values.values()):raise SystemExit('Paths contain unsupported Compose environment characters')
    env=home/'compose.env';env.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));env.chmod(0o600)
    command=compose(home,args.gpu)
    subprocess.run(command+['config','--quiet'],check=True)
    if args.action=='check':print('Host preflight passed. GPU rendering and performance still require output acceptance.');return
    if args.action=='start':
        if subprocess.run(['docker','buildx','version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
            raise SystemExit('Docker Buildx is missing; install the buildx plugin before building. Existing images can still use resume.')
        subprocess.run(command+['build'],check=True)
    # Validate and write the engine config before Docker binds that file.
    subprocess.run(command+['run','--rm','--no-deps','--pull','never','validate'],check=True)
    if args.action=='resume':
        # Xauthority and the desktop audio socket can be replaced at each login.
        # Recreate only the engine so Docker binds their current inodes.
        subprocess.run(command+['up','-d','--no-build','--pull','never','--force-recreate','engine'],check=True)
    launch=command+['up','-d','--no-build','--pull','never']
    if args.action in ('start','restart'):launch+=['--force-recreate']
    subprocess.run(launch,check=True)
    print('Station started. Check status, then inspect picture/audio and recording evidence.')

if __name__=='__main__':main()
