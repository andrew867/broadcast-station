# SPDX-License-Identifier: Apache-2.0
"""Record bounded, read-only station observations without decoding another video stream."""
import argparse,json,math,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stationctl import compose
from tools.station_watchdog import host_ports,studio_host


def summarize(rows,started,requested,complete=False):
    rates=[r['fps'] for r in rows if type(r.get('fps')) in (int,float) and math.isfinite(r['fps'])]
    gaps=[b['at']-a['at'] for a,b in zip(rows,rows[1:])]
    return {'started_at':started,'checked_at':rows[-1]['at'] if rows else started,'requested_seconds':requested,
        'complete':complete,'samples':len(rows),'probe_failures':sum(bool(r.get('error')) for r in rows),
        'not_ready_samples':sum(not r.get('ready',False) for r in rows),
        'low_fps_samples':sum(r.get('fps') is not None and r['fps']<r.get('target_fps',30)*.95 for r in rows),
        'fps_min':min(rates,default=None),'fps_max':max(rates,default=None),'fps_mean':sum(rates)/len(rates) if rates else None,
        'largest_observation_gap_seconds':max(gaps,default=0),
        'camera_unready_samples':sum(bool(r.get('unready_cameras')) for r in rows),
        'source_unready_samples':sum(bool(r.get('unready_sources')) for r in rows),
        'source_probe_failures':sum(bool(r.get('source_probe_unavailable')) for r in rows),
        'scope':'Sampled status and resources; recordings, listening, restart review and operator acceptance remain required. No automatic pass verdict.'}


def get(url):
    with urllib.request.urlopen(url,timeout=8) as response:return json.load(response)


def source_state(home,enabled,now=None):
    data=json.loads((home/'data/source-health.json').read_text())
    if now is None:now=time.time()
    if not 0<=now-data['checked_at']<3:raise ValueError('Stale source observer')
    result={}
    for key in enabled:
        source=data.get('cameras',{}).get(key,{})
        age=now-source.get('last_frame_at',0)
        result[key]={'ready':source.get('ready') is True and 0<=age<2.5,
                     'age_s':round(age,3) if 0<=age<900 else None,'generation':source.get('generation')}
    return result


def observe(home,gpu):
    _,port=host_ports(home);base=f'http://{studio_host(home)}:{port}'
    row={'at':time.time()}
    try:
        payload=get(base+'/api/broadcast');p=payload.get('playout',{});out=p.get('output',{})
        enabled={c['id'] for c in payload.get('camera_sources',[]) if c.get('enabled',True)}
        row.update(ready=p.get('ready') is True,moving=out.get('moving') is True,fps=out.get('measured_fps'),target_fps=out.get('target_fps',30),
                   frame=out.get('frames'),scene=p.get('program',{}).get('camera'),
                   unready_cameras=sorted(k for k in enabled if not p.get('cameras',{}).get(k,{}).get('ready')))
        try:
            row['decoded_sources']=source_state(home,enabled)
            row['unready_sources']=sorted(k for k,v in row['decoded_sources'].items() if not v['ready'])
        except (OSError,ValueError,KeyError,TypeError):row['source_probe_unavailable']=True
    except Exception:row['error']='Controller probe unavailable'
    try:
        state=json.loads((home/'runtime/watchdog.json').read_text())
        row['watchdog']={k:state.get(k) for k in ('controller_ok','controller_age_s','maintenance','error','history')}
    except (OSError,ValueError):row['watchdog_unavailable']=True
    try:
        ids=subprocess.check_output(compose(home,gpu)+['ps','-q'],text=True,stderr=subprocess.DEVNULL,timeout=10).split()
        if ids:
            raw=subprocess.check_output(['docker','inspect',*ids],text=True,stderr=subprocess.DEVNULL,timeout=10)
            row['services']={r['Config'].get('Labels',{}).get('com.docker.compose.service','unknown'):
                {'started':r['State']['StartedAt'],'restarts':r['RestartCount'],'oom':r['State']['OOMKilled'],'running':r['State']['Running']} for r in json.loads(raw)}
            raw=subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}',*ids],text=True,stderr=subprocess.DEVNULL,timeout=10)
            row['resources']=[{k:r.get(k) for k in ('Name','CPUPerc','MemUsage','BlockIO','PIDs')} for r in map(json.loads,raw.splitlines())]
    except (OSError,ValueError,subprocess.SubprocessError):row['resource_probe_unavailable']=True
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('home',type=Path);parser.add_argument('folder',type=Path)
    parser.add_argument('--seconds',type=int,default=86400);parser.add_argument('--interval',type=int,default=30)
    parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');args=parser.parse_args()
    if not 60<=args.seconds<=86400 or not 10<=args.interval<=300:parser.error('Choose 60 to 86400 seconds and an interval of 10 to 300 seconds')
    args.folder.mkdir(parents=True,exist_ok=False);args.folder.chmod(0o700)
    started=time.time();deadline=time.monotonic()+args.seconds;rows=[]
    with (args.folder/'samples.jsonl').open('x') as stream:
        while True:
            row=observe(args.home.resolve(),args.gpu);stream.write(json.dumps(row)+'\n');stream.flush()
            rows.append({k:v for k,v in row.items() if k not in ('resources','services','watchdog')})
            complete=time.monotonic()>=deadline
            path=args.folder/'summary.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(summarize(rows,started,args.seconds,complete),indent=2));tmp.replace(path)
            if complete:break
            time.sleep(min(args.interval,max(0,deadline-time.monotonic())))


if __name__=='__main__':main()
