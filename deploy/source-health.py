"""Independent source decoders from the saved camera registry. READY means a complete, recent decoded frame.

Software decoding is the portable baseline. Set STATION_HEALTH_VAAPI to an
available render device for hardware health decoding; qualify it on the host.
"""
import json
import os
from pathlib import Path
import selectors
import subprocess
import threading
import time
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skycam.station_config import bootstrap
bootstrap()
DATA=Path(os.environ.get('SKYCAM_DATA',ROOT/'data'))
from skycam.source_routing import camera_base
from skycam.network_health import NetworkHealth
from skycam.source_frames import FrameReader,write_thumbnail,WIDTH,HEIGHT
STATUS={};LOCK=threading.Lock()
NETWORK={}

def decoder_options(vaapi,scaling='hardware',sample_stride=1):
    if scaling not in ('hardware','software'):raise ValueError('Unknown health scaling backend')
    if type(sample_stride) is not int or not 1<=sample_stride<=6:raise ValueError('Health sample stride must be 1 to 6')
    # Decode the entire source, but avoid downloading/resizing every frame on
    # small shared GPUs. select never duplicates a picture to manufacture
    # readiness, unlike an fps filter. Source timestamps may restart safely.
    sample=f"select='not(mod(n,{sample_stride}))'," if sample_stride>1 else ''
    if not vaapi:return ['-threads','1'],sample+'scale=640:360,format=nv12'
    decode=['-hwaccel','vaapi','-hwaccel_device',vaapi,'-hwaccel_output_format','vaapi','-threads','1']
    filters=('scale_vaapi=w=640:h=360,hwdownload,format=nv12' if scaling=='hardware'
             else 'hwdownload,format=nv12,scale=640:360,format=nv12')
    return decode,sample+filters

def network_watch():
    global NETWORK
    monitor=NetworkHealth()
    while True:
        try:NETWORK=monitor.sample()
        except Exception:NETWORK={'at':time.time(),'error':'Link observation unavailable'}
        time.sleep(10)

def worker(camera,media_path,stop,source_url=None):
    generation=0
    thumbnail=(DATA/'runtime'/'confidence')/(camera+'.jpg')
    thumbnail.parent.mkdir(parents=True,exist_ok=True)
    while not stop.is_set():
        generation+=1;frames=0;last=0.;reader=FrameReader();last_thumb=0.;started=time.monotonic()
        vaapi=os.environ.get('STATION_HEALTH_VAAPI','')
        decode,filters=decoder_options(vaapi,os.environ.get('STATION_HEALTH_SCALE','hardware'),int(os.environ.get('STATION_HEALTH_SAMPLE_STRIDE','1')))
        args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-timeout','15000000','-buffer_size','4194304',
              *decode,
              '-rtsp_transport','tcp','-filter_threads','1','-i',source_url or f'{camera_base(DATA)}/{media_path}',
              '-vf',filters,'-map','0:v:0','-an','-fps_mode','passthrough','-f','rawvideo','pipe:1']
        process=None
        try:
            process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                while process.poll() is None and not stop.is_set():
                    for event,_ in selector.select(.5):
                        chunk=os.read(event.fd,65536)
                        if not chunk:break
                        count,frame=reader.feed(chunk)
                        if count:
                            frames+=count;last=time.time()
                            if time.monotonic()-last_thumb>=5:
                                last_thumb=time.monotonic()
                                try:write_thumbnail(frame,thumbnail)
                                except (OSError,ValueError):pass  # A thumbnail write must not restart camera acquisition.
                    age=time.time()-last if last else None
                    with LOCK:STATUS[camera]={'last_frame_at':last,'frames':frames,'generation':generation,
                        'ready':frames>=3 and age is not None and age<2.5,
                        'state':'ready' if frames>=3 and age is not None and age<2.5 else 'warming',
                        'monitor_size':[WIDTH,HEIGHT],'error':None}
                    if (last and time.time()-last>15) or (not last and time.monotonic()-started>30):
                        raise RuntimeError('No recent decoded video frame')
            raise RuntimeError('Camera reader disconnected')
        except Exception as exc:
            with LOCK:STATUS[camera]={'last_frame_at':last,'frames':frames,'generation':generation,
                'ready':False,'state':'reconnecting','error':'Camera decoder unavailable; reconnecting'}
        finally:
            if process:
                process.terminate()
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        stop.wait(10)

def main():
    import cv2
    cv2.setNumThreads(1)
    threading.Thread(target=network_watch,daemon=True).start()
    workers={}
    DATA.mkdir(parents=True,exist_ok=True)
    path=DATA/'source-health.json'
    registry=DATA/'broadcast'/'cameras.json'
    while True:
        try:
            rows={r['id']:r for r in json.loads(registry.read_text())['cameras']}
            base=camera_base(DATA)
            for camera,(feed,stop,thread) in list(workers.items()):
                if camera not in rows or not rows[camera]['enabled'] or feed!=(rows[camera]['media_path'],base) or not thread.is_alive():
                    stop.set();thread.join(timeout=4);workers.pop(camera)
                    with LOCK:STATUS.pop(camera,None)
            for camera,row in rows.items():
                if row['enabled'] and camera not in workers:
                    stop=threading.Event();thread=threading.Thread(target=worker,args=(camera,row['media_path'],stop,base+'/'+row['media_path']),daemon=True)
                    workers[camera]=((row['media_path'],base),stop,thread);thread.start()
                elif not row['enabled']:
                    with LOCK:STATUS[camera]={'ready':False,'state':'disabled','last_frame_at':0,'error':None}
        except (OSError,ValueError,KeyError):pass  # Keep existing readers through an incomplete registry refresh.
        with LOCK:payload=json.dumps({'checked_at':time.time(),'cameras':STATUS,'network':NETWORK})
        tmp=path.with_suffix('.tmp');tmp.write_text(payload);tmp.replace(path)
        time.sleep(.5)

if __name__=='__main__':main()
