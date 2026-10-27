# SPDX-License-Identifier: Apache-2.0
"""Install station-specific user services for bounded recovery and KDE HDMI wakefulness."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]


def monitor_url(value):
    url=urlsplit(value)
    if url.scheme not in ('rtsp','rtmp','http','https') or not url.hostname or url.username or url.password or url.query or url.fragment or any(ord(c)<33 for c in value):
        raise ValueError('Use a separate program monitor URL without credentials or query tokens')
    return value


def quote(value):
    value=str(value)
    if any(ord(c)<32 for c in value):raise ValueError('Control characters are not supported in service arguments')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%').replace('$','$$')+'"'


def units(home,gpu,url,display=False,python=sys.executable,headless=False):
    if headless and display:raise ValueError('Headless services cannot manage a desktop display')
    prefix='station-'+hashlib.sha256(str(home).encode()).hexdigest()[:10]
    jobs={'watchdog':('Recover stalled station output','station_watchdog.py',[str(home),'--gpu',gpu,'--monitor-url',monitor_url(url),'--recover'])}
    if display:jobs['display']=('Keep station HDMI output awake','keep_display_awake.py',[str(home),'--gpu',gpu])
    result={}
    for name,(description,script,arguments) in jobs.items():
        argv=[python,str(ROOT/'tools'/script),*arguments]
        session='' if headless else 'After=graphical-session.target\nPartOf=graphical-session.target\n'
        result[prefix+'-'+name+'.service']='[Unit]\nDescription='+description+'\n'+session+'StartLimitIntervalSec=300\nStartLimitBurst=5\n\n[Service]\nType=simple\nExecStart='+ ' '.join(map(quote,argv))+'\nRestart=on-failure\nRestartSec=10\nTimeoutStopSec=10\nUMask=0077\n\n[Install]\nWantedBy='+('default.target' if headless else 'graphical-session.target')+'\n'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','remove']);parser.add_argument('home',type=Path)
    parser.add_argument('--monitor-url');parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia')
    parser.add_argument('--display',action='store_true');parser.add_argument('--no-start',action='store_true')
    args=parser.parse_args()
    if sys.platform!='linux':raise SystemExit('Runtime services require Linux with user systemd')
    home=args.home.resolve();folder=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'systemd/user'
    prefix='station-'+hashlib.sha256(str(home).encode()).hexdigest()[:10]
    if args.action=='remove':
        for suffix in ('watchdog','display'):
            path=folder/(prefix+'-'+suffix+'.service')
            if path.exists():
                subprocess.run(['systemctl','--user','disable','--now',path.name],check=True);path.unlink()
        subprocess.run(['systemctl','--user','daemon-reload'],check=True);return
    if not (home/'compose.env').is_file():raise SystemExit('Run stationctl check successfully first')
    if not args.monitor_url:raise SystemExit('--monitor-url is required')
    if args.display:
        try:__import__('dbus')
        except ImportError:raise SystemExit('Install the host Python D-Bus package for KDE display inhibition')
    headless=json.loads((home/'station.json').read_text()).get('output',{}).get('headless',False)
    rows=units(home,args.gpu,args.monitor_url,args.display,headless=headless);folder.mkdir(parents=True,exist_ok=True)
    for name,body in rows.items():
        path=folder/name;path.write_text(body);path.chmod(0o600)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    for name in rows:
        subprocess.run(['systemctl','--user','enable',name],check=True)
        if not args.no_start:subprocess.run(['systemctl','--user','restart',name],check=True)
    print('Station runtime services installed. Configure desktop or headless startup separately.')


if __name__=='__main__':main()
