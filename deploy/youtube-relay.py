"""MediaMTX runOnAvailable supervisor for one SkyCam relay, not all FFmpeg jobs.

The private JSON contains the existing FFmpeg argument array. Never print it.
MediaMTX owns retries. This process exits after a stalled child is stopped.
"""
import argparse,json,os,re,selectors,signal,subprocess,time
from pathlib import Path

def redact(text):return re.sub(r'(?:rtmps?|rtsps?|https?|srt)://[^\s\"\x27]+','[stream URL redacted]',text)

class Progress:
    def __init__(self,now):self.frame=0;self.media_us=0;self.frame_at=now;self.time_at=now
    def update(self,fields,now):
        for field,attribute,timestamp in [('frame','frame','frame_at'),('out_time_us','media_us','time_at')]:
            try:value=int(fields[field])
            except (KeyError,TypeError,ValueError):continue
            if value>getattr(self,attribute):setattr(self,timestamp,now)
            setattr(self,attribute,value)
    def stalled(self,now,seconds):return now-self.frame_at>seconds or now-self.time_at>seconds

def supervised_args(args):
    if not args or Path(args[0]).name!='ffmpeg' or args.count('-i')!=1:raise ValueError('Expected the single-input FFmpeg relay')
    result=list(args);i=result.index('-i');result[i:i]=['-rw_timeout','15000000']
    result[-1:-1]=['-rw_timeout','15000000']
    return result[:1]+['-hide_banner','-nostdin','-nostats','-loglevel','warning','-stats_period','2','-progress','pipe:1']+result[1:]

def supervise(args,status_path,stall_seconds=45,stop_seconds=8):
    status_path=Path(status_path);status_path.parent.mkdir(parents=True,exist_ok=True)
    child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,start_new_session=True)
    progress=Progress(time.monotonic());stopping=False;reason='running';started=time.time();last_write=0
    def stop(*_):
        nonlocal stopping,reason
        stopping=True;reason='MediaMTX stopped this relay'
    old={sig:signal.signal(sig,stop) for sig in [signal.SIGTERM,signal.SIGINT]}
    def save(state):
        payload={'state':state,'checked_at':time.time(),'started_at':started,'pid':child.pid,'frames':progress.frame,'media_time_us':progress.media_us,
                 'frame_age_s':round(time.monotonic()-progress.frame_at,2),'reason':reason}
        tmp=status_path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,indent=2));tmp.replace(status_path)
    print('SkyCam YouTube relay starting, progress supervision enabled.',flush=True)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ,'progress');selector.register(child.stderr,selectors.EVENT_READ,'error')
            buffers={'progress':b'','error':b''};fields={}
            while child.poll() is None and not stopping:
                for key,_ in selector.select(.5):
                    chunk=os.read(key.fd,65536)
                    if not chunk:selector.unregister(key.fileobj);continue
                    kind=key.data;buffers[kind]+=chunk
                    while b'\n' in buffers[kind]:
                        line,buffers[kind]=buffers[kind].split(b'\n',1);line=line.decode(errors='replace').strip()
                        if kind=='error':
                            if line:print(redact(line)[:1500],flush=True)
                        elif '=' in line:
                            k,v=line.split('=',1);fields[k]=v
                            if k=='progress':progress.update(fields,time.monotonic());fields={}
                    if len(buffers[kind])>65536:buffers[kind]=b''
                now=time.monotonic()
                if progress.stalled(now,stall_seconds):reason='Video or media clock stalled';break
                if now-last_write>=2:save('publishing' if progress.frame>0 else 'connecting');last_write=now
        if child.poll() is not None and not stopping:reason='FFmpeg exited with code '+str(child.returncode)
    finally:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=stop_seconds)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
        save('stopped' if stopping else 'restarting')
        for sig,handler in old.items():signal.signal(sig,handler)
        print('SkyCam YouTube relay: '+reason,flush=True)
    return 0 if stopping else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='/etc/skycam-youtube-relay.json');parser.add_argument('--status',default='/var/lib/skycam-relay/status.json');options=parser.parse_args()
    try:args=supervised_args(json.loads(Path(options.config).read_text())['args'])
    except Exception:raise SystemExit('Private SkyCam relay configuration could not be loaded')
    raise SystemExit(supervise(args,options.status))
