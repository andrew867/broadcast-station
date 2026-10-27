"""Compact one-minute performance records, bounded to 24 hours and hourly files."""
import json,math,threading,time
from pathlib import Path

class PerformanceHistory:
    def __init__(self,folder,now=None):
        self.folder=Path(folder);self.lock=threading.RLock();self.rows=[];self.current=None;self.error=None
        now=time.time() if now is None else now
        try:
            self.folder.mkdir(parents=True,exist_ok=True)
            for path in sorted(self.folder.glob('hour-*.jsonl'))[-25:]:
                if path.stat().st_size>4_000_000:continue
                for line in path.read_text(encoding='utf-8').splitlines():
                    try:
                        r=json.loads(line)
                        if self.valid(r) and now-86400<=r['at']<=now:self.rows.append(r)
                    except (ValueError,TypeError):continue
            self.rows=sorted({r['at']:r for r in self.rows}.values(),key=lambda r:r['at'])[-1440:]
        except OSError:self.error='Saved performance history could not be read'

    @staticmethod
    def valid(r):
        base=(isinstance(r,dict) and isinstance(r.get('at'),(int,float)) and math.isfinite(r['at'])
                and all(isinstance(r.get(k),int) and 0<=r[k]<=1000 for k in ('samples','valid','missing','transitions','fallback_cuts'))
                and isinstance(r.get('fps_sum'),(int,float)) and math.isfinite(r['fps_sum'])
                and all(r.get(k) is None or isinstance(r[k],(int,float)) and math.isfinite(r[k]) for k in ('min_fps','max_fps')))
        if not base or r['valid']+r['missing']!=r['samples']:return False
        scenes=r.get('scenes',{})
        return (isinstance(scenes,dict) and len(scenes)<=64 and
                all(isinstance(k,str) and len(k)<=48 and isinstance(g,dict) and
                    isinstance(g.get('samples'),int) and 0<g['samples']<=1000 and
                    isinstance(g.get('fps_sum'),(int,float)) and math.isfinite(g['fps_sum']) for k,g in scenes.items()))

    def add(self,sample):
        at=sample['at'];minute=int(at//60)*60
        with self.lock:
            if self.current and minute<self.current['at']:return
            if self.current and minute!=self.current['at']:self.flush(at)
            if self.current is None:
                if self.rows and minute<=self.rows[-1]['at']:return
                self.current={'at':minute,'samples':0,'valid':0,'missing':0,'fps_sum':0.,'min_fps':None,'max_fps':None,
                    'transitions':0,'fallback_cuts':0,'scenes':{},'source_unavailable':{},'memory_available_min':None,'graphics_device_max':None}
                self.seen=set()
            r=self.current;r['samples']+=1;fps=sample.get('fps')
            if isinstance(fps,(int,float)) and math.isfinite(fps):
                r['valid']+=1;r['fps_sum']+=fps;r['min_fps']=fps if r['min_fps'] is None else min(r['min_fps'],fps);r['max_fps']=fps if r['max_fps'] is None else max(r['max_fps'],fps)
                scene=str(sample.get('scene') or 'unknown')[:48]
                if scene in r['scenes'] or len(r['scenes'])<64:
                    g=r['scenes'].setdefault(scene,{'samples':0,'fps_sum':0.});g['samples']+=1;g['fps_sum']+=fps
            else:r['missing']+=1
            t=sample.get('transition') or {};event=t.get('at')
            if isinstance(event,(float,int)) and minute<=event<minute+60 and event not in self.seen:
                self.seen.add(event);r['transitions']+=1;r['fallback_cuts']+=bool(t.get('fallback_cut'))
            for key,s in list(sample.get('sources',{}).items())[:64]:
                if s.get('display') in ('loading','reconnecting'):
                    r['source_unavailable'][key]=r['source_unavailable'].get(key,0)+1
            memory=(sample.get('memory') or {}).get('available_bytes');gpu=(sample.get('graphics') or {}).get('device_bytes')
            for key,v,fn in [('memory_available_min',memory,min),('graphics_device_max',gpu,max)]:
                if isinstance(v,(int,float)) and math.isfinite(v) and v>=0:r[key]=v if r[key] is None else fn(r[key],v)

    def flush(self,now):
        r=self.current
        if not r:return
        self.rows=[x for x in self.rows if x['at']>=now-86400]
        self.rows.append(r);self.rows=self.rows[-1440:];self.current=None
        try:
            path=self.folder/f"hour-{int(r['at']//3600)}.jsonl"
            with path.open('a',encoding='utf-8') as f:f.write(json.dumps(r,separators=(',',':'))+'\n')
            for p in self.folder.glob('hour-*.jsonl'):
                try:hour=int(p.stem.split('-',1)[1])
                except ValueError:continue
                if hour<int((now-86400)//3600):p.unlink(missing_ok=True)
            self.error=None
        except OSError:self.error='Performance history could not be saved; program is unaffected'

    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            rows=json.loads(json.dumps([r for r in self.rows if now-86400<=r['at']<=now]+([self.current] if self.current and now-86400<=self.current['at']<=now else [])))
            error=self.error
        n=sum(r['valid'] for r in rows);scenes={}
        for r in rows:
            for key,g in r.get('scenes',{}).items():
                s=scenes.setdefault(key,{'samples':0,'fps_sum':0});s['samples']+=g['samples'];s['fps_sum']+=g['fps_sum']
        return {'minutes':rows,'error':error,'retention_hours':24,'summary':{'minutes_observed':len(rows),'valid_samples':n,
            'missing_samples':sum(r['missing'] for r in rows),'average_fps':round(sum(r['fps_sum'] for r in rows)/n,2) if n else None,
            'fallback_cuts':sum(r['fallback_cuts'] for r in rows),'transitions':sum(r['transitions'] for r in rows),
            'scenes':{k:{'samples':v['samples'],'average_fps':round(v['fps_sum']/v['samples'],2)} for k,v in scenes.items() if v['samples']}},
            'limits':'One-minute summaries of five-second output-counter observations. Missing minutes remain gaps, not zero or healthy output. Saved once per completed minute; the active minute can be lost on restart. Not unique-picture FPS or proof of downstream playback.'}
