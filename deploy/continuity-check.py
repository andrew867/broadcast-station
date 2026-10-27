"""Bounded, read-only observation. Never restart or modify broadcast services."""
import argparse,json,math,subprocess,sys,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skycam.music_status import split_status

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8765/api/'+path,timeout=5) as r:return json.load(r)
def observe():
    row={'at':time.time()}
    for path in ['broadcast','rundown','music']:
        try:
            d=get(path)
            if path=='broadcast':row.update(scene=d['state']['camera'],output=d['playout'].get('output'),playout_error=d['playout'].get('error'),connected=d['playout'].get('connected'),sources={k:{f:v.get(f) for f in ['ready','native_ready','moving','state','playout_active','display','native_frame_age_s']} for k,v in d['playout'].get('cameras',{}).items()})
            elif path=='rundown':row['rundown']={k:d.get(k) for k in ['enabled','index','error']}
            else:row['music']={k:d.get(k) for k in ['enabled','current','error','note']}
        except Exception as exc:row[path+'_error']=str(exc)[:160]
    try:row['engine']=subprocess.check_output(['docker','inspect','-f','{{.State.StartedAt}}','skycam-caspar'],text=True,timeout=5).strip()
    except Exception as exc:row['engine_error']=str(exc)[:160]
    try:
        values={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
        row['host_memory_kb']={key:values[key] for key in ['MemAvailable','SwapFree']}
    except (OSError,ValueError,KeyError):pass
    return row
def summarize(rows,done):
    rates=[r['output']['measured_fps'] for r in rows if r.get('output')
           and type(r['output'].get('measured_fps')) in (int,float)
           and math.isfinite(r['output']['measured_fps']) and r['output']['measured_fps']>=0]
    errors=[];information=[]
    for row in rows:
        issues={k:v for k,v in row.items() if k.endswith('_error') and v}
        for service in ('music','rundown'):
            if (row.get(service) or {}).get('error'):
                error,note=split_status(row[service]['error']) if service=='music' else (row[service]['error'],None)
                if error:issues[service+'_reported_error']=error
                if note:information.append({'at':row['at'],'music_note':note})
        if (row.get('music') or {}).get('note'):
            information.append({'at':row['at'],'music_note':row['music']['note']})
        if issues:errors.append({'at':row['at'],**issues})
    sources={}
    for name in sorted({name for row in rows for name in row.get('sources',{})}):
        known=[row['sources'][name].get('ready') for row in rows if name in row.get('sources',{})]
        # Native-ready is normally false for inputs not selected for playout.
        # Only independent decoded-source readiness belongs in this count.
        sources[name]={'observations':len(known),'ready_samples':sum(v is True for v in known),
                       'not_ready_samples':sum(v is False for v in known),
                       'unknown_samples':sum(type(v) is not bool for v in known)}
    tracks=list(dict.fromkeys(r.get('music',{}).get('current') for r in rows))
    return {'complete':done,'samples':len(rows),'duration_seconds':rows[-1]['at']-rows[0]['at'],
        'engine_starts':sorted({r['engine'] for r in rows if r.get('engine')}),
        'scenes':sorted({r['scene'] for r in rows if r.get('scene')}),'tracks':tracks,
        'sampled_fps':{'min':min(rates),'max':max(rates),'mean':sum(rates)/len(rates)} if rates else None,
        'error_samples':errors,'information_samples':information,'source_readiness':sources,
        'music_status_without_current':sum(bool((r.get('music') or {}).get('enabled')) and not r['music'].get('current') for r in rows),
        'nonmoving_samples':sum(r.get('output',{}).get('moving') is False for r in rows if r.get('output')),
        'unknown_output_samples':sum(not r.get('output') for r in rows),
        'sampling_gaps': [{'from':a['at'],'to':b['at'],'seconds':round(b['at']-a['at'],2)} for a,b in zip(rows,rows[1:]) if b['at']-a['at']>30],
        'minimum_available_memory_mb':min([r['host_memory_kb']['MemAvailable']/1024 for r in rows if r.get('host_memory_kb')],default=None),
        'claim_limit':'Status sampling only. Not proof of audible quality, per-frame continuity, reboot or outage recovery.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=7200);p.add_argument('--folder',required=True);args=p.parse_args()
    out=Path(args.folder);out.mkdir(parents=True,exist_ok=True)
    log=out/'observations.jsonl'
    rows=[json.loads(line) for line in log.read_text().splitlines() if line.strip()] if log.exists() else []
    while True:
        row=observe();rows.append(row)
        with (out/'observations.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        done=row['at']-rows[0]['at']>=args.seconds
        tmp=out/'summary.tmp';tmp.write_text(json.dumps(summarize(rows,done),indent=2));tmp.replace(out/'summary.json')
        if done:break
        time.sleep(10)
    print(json.dumps(summarize(rows,True),indent=2))
