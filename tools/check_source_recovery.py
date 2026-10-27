# SPDX-License-Identifier: Apache-2.0
"""Exercise fan-out and decoded-frame recovery with an isolated synthetic camera."""
import json,os,signal,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def run():
    with tempfile.TemporaryDirectory(prefix='station-reconnect-') as tmp:
        root=Path(tmp);data=root/'data';(data/'broadcast').mkdir(parents=True)
        registry={'version':1,'cameras':[{'id':'cam1','enabled':True,'media_path':'cam1'}]}
        (data/'broadcast/cameras.json').write_text(json.dumps(registry))
        config={'inputs':{'camera_base':'rtsp://127.0.0.1:18554','camera_shared_base':'rtsp://127.0.0.1:8554'},'data_directory':str(data)}
        (root/'station.json').write_text(json.dumps(config));(data/'broadcast/source-routing.json').write_text('{"shared_camera_inputs":true}')
        upstream={'rtspAddress':':18554','rtspTransports':['tcp'],'rtmp':False,'hls':False,'webrtc':False,'srt':False,'paths':{'cam1':{'source':'publisher'}}}
        (root/'upstream.json').write_text(json.dumps(upstream))
        env={**os.environ,'STATION_CONFIG':str(root/'station.json'),'SKYCAM_DATA':str(data),'STATION_OFFLINE':'0','PYTHONPATH':str(ROOT)}
        children=[];logs=[]
        def start(args):
            log=open(root/('process-'+str(len(logs))+'.log'),'wb');logs.append(log)
            p=subprocess.Popen(args,env=env,stdout=log,stderr=log);children.append(p);return p
        def stop(p):
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        def state():
            try:return json.loads((data/'source-health.json').read_text()).get('cameras',{}).get('cam1',{})
            except (OSError,ValueError):return {}
        def wait_for(predicate,seconds,label):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                if predicate():return
                time.sleep(.25)
            raise RuntimeError(label+' timed out; '+json.dumps(state()))
        def publisher():return start(['ffmpeg','-hide_banner','-loglevel','error','-re','-f','lavfi','-i','testsrc2=size=320x180:rate=10','-an','-c:v','libx264','-threads','1','-preset','ultrafast','-tune','zerolatency','-g','10','-f','rtsp','-rtsp_transport','tcp','rtsp://127.0.0.1:18554/cam1'])
        try:
            start(['/usr/local/bin/mediamtx',str(root/'upstream.json')]);time.sleep(1)
            start(['python','deploy/camera-hub.py']);time.sleep(1)
            start(['python','deploy/source-health.py']);pub=publisher()
            wait_for(lambda:state().get('ready') is True,65,'Initial decoded readiness')
            # Readiness must remain true between sparse confidence thumbnails.
            # The former multi-output FFmpeg graph paused health delivery for five seconds.
            samples=[];until=time.monotonic()+12
            while time.monotonic()<until:
                sample=state();samples.append(sample)
                assert sample.get('ready') is True, 'Healthy source became unavailable between confidence pictures'
                time.sleep(.25)
            first=state();stop(pub)
            wait_for(lambda:state().get('ready') is False,30,'Source loss detection')
            lost=state();publisher()
            wait_for(lambda:state().get('ready') is True and state().get('generation',0)>first.get('generation',0),75,'Decoded recovery')
            recovered=state()
            assert (data/'runtime/confidence/cam1.jpg').is_file()
            print(json.dumps({'initial_ready':True,'loss_detected':True,'recovered_ready':True,'initial_generation':first['generation'],'recovered_generation':recovered['generation'],'confidence_picture':True,'input':'synthetic 320x180 10fps','scope':'Camera fan-out and health recovery, not program output'},indent=2))
        finally:
            for p in reversed(children):stop(p)
            for log in logs:log.close()

if __name__=='__main__':run()
