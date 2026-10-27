"""Bounded packet-timestamp observation. No decoding, encoding or recovery actions."""
import argparse,json,math,selectors,subprocess,time
from pathlib import Path

class PacketStats:
    def __init__(self):
        self.streams={};self.events=[]

    def add(self,kind,pts,at):
        if kind not in ('audio','video') or not math.isfinite(pts):return
        row=self.streams.setdefault(kind,{'packets':0,'first_pts':pts,'last_pts':None,
            'max_step':0.,'nonincreasing':0,'large_gaps':0,'last_received_at':at})
        previous=row['last_pts']
        if previous is not None:
            step=pts-previous
            row['max_step']=max(row['max_step'],step)
            if step<=0:row['nonincreasing']+=1
            threshold=.05 if kind=='audio' else .08
            if step>threshold or step<=0:
                row['large_gaps']+=step>threshold
                self.events.append({'at':at,'stream':kind,'from':previous,'to':pts,'seconds':step})
                self.events=self.events[-64:]
        row['last_pts']=pts;row['last_received_at']=at;row['packets']+=1

    def reset_connection(self):
        # A new subscription has its own epoch. Do not hide it or call it a
        # continuous timestamp interval through the reconnect.
        for row in self.streams.values():row['last_pts']=None

def monitor(url,folder,seconds):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    stats=PacketStats();started=time.time();deadline=time.monotonic()+seconds
    generations=0;errors=[];last_write=0;last_logged_event=None;process=None
    def save(done=False):
        nonlocal last_logged_event
        now=time.time()
        report={'started_at':started,'checked_at':now,'elapsed_seconds':now-started,
            'requested_seconds':seconds,'complete':done,'connections':generations,
            'streams':stats.streams,'recent_events':stats.events,'connection_errors':errors[-20:],
            'claim_limit':'Packet timestamps only. No decoded-picture or audible-quality claim; reconnects are explicit.'}
        temp=folder/'summary.tmp';temp.write_text(json.dumps(report,indent=2));temp.replace(folder/'summary.json')
        with (folder/'minutes.jsonl').open('a') as f:
            f.write(json.dumps({k:v for k,v in report.items() if k not in ('recent_events','connection_errors')})+'\n')
        if stats.events and stats.events[-1]!=last_logged_event:
            with (folder/'events.jsonl').open('a') as f:
                for row in stats.events:
                    if last_logged_event is None or row['at']>last_logged_event['at']:f.write(json.dumps(row)+'\n')
            last_logged_event=stats.events[-1]
    try:
        while time.monotonic()<deadline:
            args=['ffprobe','-v','error','-rw_timeout','8000000']
            if url.startswith('rtsp:'):args+=['-rtsp_transport','tcp']
            args+=['-show_packets','-show_entries','packet=codec_type,dts_time','-of','compact',url]
            with (folder/'probe.log').open('w') as log:
                process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=log,bufsize=0)
                generations+=1;stats.reset_connection();buffer=b''
                try:
                    with selectors.DefaultSelector() as sel:
                        sel.register(process.stdout,selectors.EVENT_READ)
                        while time.monotonic()<deadline and process.poll() is None:
                            if sel.select(1):
                                chunk=process.stdout.read(65536)
                                if not chunk:break
                                buffer+=chunk
                                while b'\n' in buffer:
                                    line,buffer=buffer.split(b'\n',1)
                                    row=dict(x.split(b'=',1) for x in line.split(b'|')[1:] if b'=' in x)
                                    try:stats.add(row[b'codec_type'].decode(),float(row[b'dts_time']),time.time())
                                    except (KeyError,ValueError):pass
                            if time.monotonic()-last_write>=60:
                                if log.tell()>128_000:log.seek(0);log.truncate()
                                save();last_write=time.monotonic()
                finally:
                    process.terminate()
                    try:process.wait(3)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                if time.monotonic()<deadline:
                    errors.append({'at':time.time(),'exit':process.returncode})
                    errors=errors[-20:];time.sleep(min(3,max(0,deadline-time.monotonic())))
        save(True)
    finally:
        if process and process.poll() is None:process.kill();process.wait()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True);parser.add_argument('--folder',required=True)
    parser.add_argument('--seconds',type=int,default=28800)
    a=parser.parse_args()
    if not 1<=a.seconds<=86400:parser.error('Choose a duration from 1 second to 24 hours')
    monitor(a.url,a.folder,a.seconds)
