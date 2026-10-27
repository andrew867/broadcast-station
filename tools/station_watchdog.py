# SPDX-License-Identifier: Apache-2.0
"""Host-side Compose watchdog, using the existing bounded recovery guard."""
import argparse,importlib.util,json,math,socket,subprocess,time,urllib.request,sys
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stationctl import compose
spec=importlib.util.spec_from_file_location('guard',ROOT/'deploy/program-watchdog.py');guard_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard_module)


def command(args,timeout=10):
    result=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Container operation failed')
    return result.stdout


def frame_counter(port):
    with socket.create_connection(('127.0.0.1',port),timeout=3) as connection:
        connection.settimeout(3);connection.sendall(b'INFO 1\r\n');data=b''
        while True:
            part=connection.recv(65536)
            if not part or len(data)>2_000_000:raise ValueError('Incomplete AMCP response')
            data+=part
            if b'<?xml' in data:
                try:root=ET.fromstring(data[data.index(b'<?xml'):].strip());break
                except ET.ParseError:pass
    if not data.startswith(b'201 '):raise ValueError('AMCP unavailable')
    values=[int(n.text) for n in root.findall('.//output/port/file/frame')]
    if not values:values=[int(n.text) for n in root.findall('.//file/frame')]
    return max(values) if values else None


def host_ports(home):
    values=dict(line.split('=',1) for line in (home/'compose.env').read_text().splitlines() if '=' in line)
    return tuple(int(values.get(k,default)) for k,default in [('STATION_AMCP_PORT','5250'),('STATION_HTTP_PORT','8765')])


def studio_host(home):
    from tools.stationctl import http_bind
    values=dict(line.split('=',1) for line in (home/'compose.env').read_text().splitlines() if '=' in line)
    return http_bind(values.get('STATION_HTTP_BIND','127.0.0.1'))


def controller_age(payload,observed_at):
    checked=payload.get('playout',{}).get('checked_at')
    if type(checked) not in (int,float) or not math.isfinite(checked):return None
    return observed_at-checked


def acquire_lock(runtime):
    if sys.platform!='linux':raise RuntimeError('The station watchdog requires Linux')
    import fcntl
    handle=(runtime/'watchdog.lock').open('a')
    try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close();raise RuntimeError('A watchdog is already watching this station') from None
    return handle


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('home',type=Path);parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');parser.add_argument('--monitor-url',required=True);parser.add_argument('--recover',action='store_true');args=parser.parse_args()
    url=urlsplit(args.monitor_url)
    if url.scheme not in ('rtsp','rtmp','http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:raise SystemExit('Use a separate program monitor URL without credentials or query tokens')
    home=args.home.resolve();base=compose(home,args.gpu);runtime=home/'runtime';runtime.mkdir(exist_ok=True)
    # Hold the descriptor for the process lifetime. Two guards must never spend
    # independent restart budgets against the same station.
    try:watchdog_lock=acquire_lock(runtime)
    except RuntimeError as exc:raise SystemExit(str(exc))
    amcp_port,http_port=host_ports(home)
    http_host=studio_host(home)
    history=home/'data/broadcast/watchdog-history.json'
    try:rows=json.loads(history.read_text()) if history.stat().st_size<256000 else []
    except (OSError,ValueError):rows=[]
    guard=guard_module.Guard(time.time(),rows);delivery=guard_module.DeliveryProbe();last_probe=0
    while True:
        now=time.time();error=None;action=None;frame=None;web_age=None;web_ok=False
        try:
            states={}
            for service in ('engine','studio'):
                identity=command(base+['ps','-a','-q',service]).strip()
                states[service]=json.loads(command(['docker','inspect','--format={{json .State}}',identity])) if identity else None
            engine=states['engine'];web=states['studio'];web_running=bool(web and web.get('Running') and not web.get('Paused'))
            maintenance=(runtime/'maintenance').exists();web_ok=False
            if engine and engine.get('Running') and not engine.get('Paused'):
                try:frame=frame_counter(amcp_port)
                except Exception:pass
                if web_running:
                    try:
                        with urllib.request.urlopen(f'http://{http_host}:{http_port}/api/broadcast',timeout=4) as response:payload=json.load(response)
                        # The controller may update while Docker/AMCP/HTTP checks
                        # are in flight. Compare with receipt time, not loop start.
                        web_age=controller_age(payload,time.time())
                        web_ok=web_age is not None and 0<=web_age<60
                    except Exception:pass
                # Probe only when primary delivery evidence is missing/stalled.
                if not maintenance and (frame is None or now-guard.changed>15) and now-last_probe>=10:
                    last_probe=now
                    try:
                        transport=['-rtsp_transport','tcp','-timeout','4000000'] if url.scheme=='rtsp' else ['-rw_timeout','4000000']
                        raw=command(['ffprobe','-v','error',*transport,'-read_intervals','%+0.5','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',args.monitor_url],timeout=7)
                        pts=[float(f['best_effort_timestamp_time']) for f in json.loads(raw).get('frames',[]) if 'best_effort_timestamp_time' in f]
                        delivery.observe(now,max(pts) if pts else None)
                    except Exception:pass
            action=guard.observe(now,engine,web_running,frame,web_ok,maintenance,now-delivery.last_advance<20)
            if action and args.recover:
                reason=guard.last_reason;guard.recovered(now,action,reason);guard_module.atomic_json(history,guard.history)
                services=['engine','studio'] if action=='engine' and web_running else ['engine'] if action=='engine' else ['studio']
                command(base+['restart','--timeout','5',*services],timeout=70)
                print('Recovered '+action+': '+reason,flush=True)
        except Exception:error='Watchdog inspection unavailable; no unverified restart requested'
        guard_module.atomic_json(runtime/'watchdog.json',{'checked_at':now,'note':guard.last_reason,'error':error,'frame':frame,'controller_ok':web_ok,'controller_age_s':web_age,'suggested_action':action,'recovery_enabled':args.recover,'history':guard.history[-3:],'recovery_budget':guard.recovery_budget(now),'maintenance':(runtime/'maintenance').exists()})
        time.sleep(5)

if __name__=='__main__':main()
