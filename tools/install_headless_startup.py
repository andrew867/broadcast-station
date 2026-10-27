# SPDX-License-Identifier: Apache-2.0
"""Install a station-specific startup service independent of desktop login."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.install_runtime_services import quote
ROOT=Path(__file__).resolve().parents[1]


def unit(home,gpu,python=sys.executable):
    name='station-'+hashlib.sha256(str(home).encode()).hexdigest()[:10]+'-headless.service'
    command=[python,str(ROOT/'tools/session_start.py'),str(home),'--gpu',gpu]
    body='[Unit]\nDescription=Start headless broadcast station\nStartLimitIntervalSec=600\nStartLimitBurst=3\n\n[Service]\nType=oneshot\nExecStart='+ ' '.join(map(quote,command))+'\nRemainAfterExit=yes\nRestart=on-failure\nRestartSec=30\nTimeoutStartSec=510\nUMask=0077\n\n[Install]\nWantedBy=default.target\n'
    return name,body


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['install','remove']);p.add_argument('home',type=Path);p.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');p.add_argument('--no-start',action='store_true');a=p.parse_args()
    if sys.platform!='linux':raise SystemExit('Headless startup requires Linux with user systemd')
    home=a.home.resolve();name,body=unit(home,a.gpu)
    folder=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'systemd/user';path=folder/name
    if a.action=='remove':
        if path.exists():subprocess.run(['systemctl','--user','disable','--now',name],check=True);path.unlink()
        subprocess.run(['systemctl','--user','daemon-reload'],check=True);return
    config=json.loads((home/'station.json').read_text())
    if not config.get('output',{}).get('headless'):raise SystemExit('Enable output.headless before installing headless startup')
    if not (home/'compose.env').exists() or 'STATION_HEADLESS=1' not in (home/'compose.env').read_text().splitlines():raise SystemExit('Run stationctl check in headless mode first')
    folder.mkdir(parents=True,exist_ok=True);path.write_text(body);path.chmod(0o600)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable',name],check=True)
    if not a.no_start:subprocess.run(['systemctl','--user','start',name],check=True)
    linger=subprocess.run(['loginctl','show-user',str(os.getuid()),'--property=Linger','--value'],capture_output=True,text=True,timeout=10)
    print('Headless startup installed. Docker restart policies preserve running services across host restarts.')
    if linger.returncode or linger.stdout.strip()!='yes':print('Boot without login also requires an administrator to enable user lingering: sudo loginctl enable-linger '+str(os.getuid()))


if __name__=='__main__':main()
