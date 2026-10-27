"""Private-container MediaMTX fan-out. One upstream copy per camera, no encoding."""
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skycam.station_config import CONFIG,bootstrap
bootstrap()
DATA=Path(os.environ.get('SKYCAM_DATA',ROOT/'data'))
from skycam.transport_health import observe_loss

def write_configuration(path,text,last_write,now):
    # MediaMTX's file watcher ignores events within one second of a reload.
    # Keep a wider interval, then write the latest complete registry on the
    # next loop. Otherwise a burst of camera edits can be saved but never used.
    if path.exists() and (path.read_text()==text or now-last_write<2):return last_write
    tmp=path.with_suffix('.tmp');tmp.write_text(text);tmp.replace(path)
    return now

def configuration(rows):
    paths={}
    for row in rows:
        name=row['media_path']
        if row.get('enabled') and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_/-]{0,127}',name):
            paths[name]={'source':CONFIG.inputs.camera_base+'/'+name,'rtspTransport':'tcp',
                         'sourceOnDemand':True,'sourceOnDemandStartTimeout':'20s','sourceOnDemandCloseAfter':'10s'}
    return {'logLevel':'warn','readTimeout':'15s','writeTimeout':'15s','writeQueueSize':4096,
            'api':False,'metrics':False,'pprof':False,'playback':False,
            'rtsp':True,'rtspAddress':':8554','rtspTransports':['tcp'],
            'rtmp':False,'hls':False,'webrtc':False,'srt':False,'moq':False,'paths':paths}

def main():
    folder=DATA/'runtime'/'camera-hub';folder.mkdir(parents=True,exist_ok=True)
    config=folder/'mediamtx.json';registry=DATA/'broadcast/cameras.json'
    last_write=float('-inf')
    def update():
        nonlocal last_write
        text=json.dumps(configuration(json.loads(registry.read_text())['cameras'] if registry.exists() else []),indent=2)
        last_write=write_configuration(config,text,last_write,time.monotonic())
    update()
    process=subprocess.Popen([os.environ.get('STATION_MEDIAMTX','/usr/local/bin/mediamtx'),str(config)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    losses={};lock=threading.Lock()
    def logs():
        for line in process.stdout:
            with lock:observe_loss(losses,line,time.time())
            pass  # Raw source errors may include credentials; status is retained separately.
    threading.Thread(target=logs,daemon=True).start()
    stopped=False
    def stop(*_):
        nonlocal stopped
        stopped=True;process.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while not stopped:
            if process.poll() is not None:raise RuntimeError('Camera hub exited')
            try:update()
            except (OSError,ValueError,KeyError) as exc:print('Retaining previous camera hub config after invalid registry update',flush=True)
            allowed=json.loads(config.read_text())['paths']
            with lock:
                for name in list(losses):
                    if name not in allowed:losses.pop(name,None)
                payload=json.dumps({'checked_at':time.time(),'paths':losses})
            status=folder.parent/'camera-transport.json';tmp=status.with_suffix('.tmp')
            tmp.write_text(payload);tmp.replace(status)
            time.sleep(1)
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':main()
