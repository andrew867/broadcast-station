"""Small host-side observations of the existing contribution link."""
from urllib.parse import urlsplit
from .station_config import CONFIG
HOST=urlsplit(CONFIG.inputs.camera_base).hostname
import re
import subprocess
import time
from pathlib import Path

def parse_ping(text):
    match=re.search(r'time[=<]([\d.]+)\s*ms',text)
    return float(match[1]) if match else None

def queue_totals(text):
    if text is None:return {'remote_connections':None,'receive_queue_bytes':None,'send_queue_bytes':None}
    rows=[line.split() for line in text.splitlines()]
    rows=[r for r in rows if len(r)>=5 and r[1].isdigit() and r[2].isdigit()]
    return {'remote_connections':len(rows),'receive_queue_bytes':sum(int(r[1]) for r in rows),
            'send_queue_bytes':sum(int(r[2]) for r in rows)}

def command(args):
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=2)
        return result.stdout if result.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None

class NetworkHealth:
    def __init__(self):self.previous=None;self.interface=None
    def sample(self):
        if not self.interface:
            match=re.search(r'\bdev (\S+)',command(['ip','route','get',HOST]) or '')
            if match:self.interface=match[1]
        now=time.monotonic();rx=tx=None
        try:
            root=Path('/sys/class/net')/self.interface/'statistics'
            current=(now,int((root/'rx_bytes').read_text()),int((root/'tx_bytes').read_text()))
            if self.previous and now>self.previous[0] and current[1]>=self.previous[1] and current[2]>=self.previous[2]:
                rx=round((current[1]-self.previous[1])*8/(now-self.previous[0])/1e6,2)
                tx=round((current[2]-self.previous[2])*8/(now-self.previous[0])/1e6,2)
            self.previous=current
        except (OSError,TypeError,ValueError):pass
        ping=command(['ping','-c','1','-W','1',HOST])
        queues=queue_totals(command(['ss','-Htn','dst',HOST]))
        return {'at':time.time(),'interface':self.interface,'rtt_ms':parse_ping(ping or ''),
                'host_rx_mbps':rx,'host_tx_mbps':tx,**queues,
                'basis':'Host interface totals, not just SkyCam. RTT is one ICMP probe to MediaMTX. Socket queues are all current TCP connections to that host.'}
