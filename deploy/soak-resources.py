"""Read-only minute snapshots for a bounded overnight observation."""
import argparse,hashlib,json,subprocess,time,urllib.request
from pathlib import Path

def command(args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=10)
        return {'exit':p.returncode,'text':p.stdout[:24000],'error':p.stderr[:400]}
    except (OSError,subprocess.TimeoutExpired) as exc:return {'error':str(exc)[:400]}

def sample(root):
    row={'at':time.time()}
    row['load']=Path('/proc/loadavg').read_text().strip()
    row['memory']=Path('/proc/meminfo').read_text()
    row['gpu']=command(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits'])
    row['containers']=command(['docker','stats','--no-stream','--format','{{json .}}','skycam-caspar','skycam-web'])
    row['engine']=command(['docker','inspect','-f','{{.State.StartedAt}} {{.RestartCount}} {{.State.OOMKilled}}','skycam-caspar'])
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/performance',timeout=8) as r:d=json.load(r)
        row['performance']=d.get('summary');row['latest_performance']=(d.get('samples') or [None])[-1]
    except Exception as exc:row['performance_error']=str(exc)[:200]
    row['settings_hashes']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [root/'casparcg.config',root/'data-web/music.json',root/'data-web/rundown.json'] if p.is_file()}
    return row

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--seconds',type=int,default=43200);a=p.parse_args()
    if not 60<=a.seconds<=86400:p.error('Choose 60 seconds to 24 hours')
    out=Path(a.folder);out.mkdir(parents=True,exist_ok=True)
    root=Path('/srv/station');start=time.time();deadline=time.monotonic()+a.seconds;count=0
    while True:
        row=sample(root);count+=1
        with (out/'resources.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        done=time.monotonic()>=deadline
        state={'started_at':start,'checked_at':time.time(),'samples':count,'complete':done,'requested_seconds':a.seconds,'read_only':True}
        tmp=out/'resources.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(out/'resources-summary.json')
        if done:break
        time.sleep(min(60,max(0,deadline-time.monotonic())))
