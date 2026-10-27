"""Bounded OFF-AIR exercise, launched only by run-camera-fault-check.py.

Private container namespace, AMCP 5351 and TCP proxy 8555.
Never commands the live engine.
"""
import json,os,select,socket,socketserver,subprocess,threading,time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image,ImageDraw
from skycam import playout as p
from skycam.camera_recovery import PicturePolicy

ROOT=Path('/review')
MODE='flowing'
SOCKETS=set()
SOCKET_LOCK=threading.Lock()

class Proxy(socketserver.BaseRequestHandler):
    def handle(self):
        if MODE=='closed':return
        try:
            upstream=socket.create_connection((os.environ['TEST_HOST_GATEWAY'],18555),3)
        except OSError:return
        peers=[self.request,upstream]
        with SOCKET_LOCK:SOCKETS.update(peers)
        try:
            while MODE!='closed':
                if MODE=='stalled':
                    time.sleep(.05);continue
                for source in select.select(peers,[],[],.2)[0]:
                    data=source.recv(65536)
                    if not data:return
                    peers[1 if source is peers[0] else 0].sendall(data)
        except (OSError,ValueError):pass
        finally:
            with SOCKET_LOCK:SOCKETS.difference_update(peers)
            upstream.close()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

def mode(value):
    global MODE
    MODE=value
    if value=='closed':
        with SOCKET_LOCK:
            for s in list(SOCKETS):
                try:s.shutdown(socket.SHUT_RDWR)
                except OSError:pass

def command(text,xml=False,**kwargs):
    # Hard-coded test port intentionally has no fallback to program's 5250.
    with socket.create_connection(('127.0.0.1',5351),3) as s:
        s.settimeout(5);s.sendall((text+'\r\n').encode());data=b''
        while True:
            part=s.recv(65536)
            if not part:raise RuntimeError('Test engine closed connection')
            data+=part
            if b'\r\n' in data and not data.startswith((b'200 ',b'201 ',b'202 ')):
                raise RuntimeError(data[:160].decode(errors='replace'))
            if xml and b'<?xml' in data:
                try:ET.fromstring(data[data.index(b'<?xml'):]);break
                except ET.ParseError:pass
            elif not xml and b'\r\n' in data:break
    return data.decode(errors='replace')

def info(ch):
    reply=command(f'INFO {ch}',xml=True)
    return ET.fromstring(reply[reply.index('<?xml'):])

def independently_decoded(url):
    run=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin',
        '-rtsp_transport','tcp','-threads','1','-i',url,'-an','-frames:v','3',
        '-vf','scale=16:16','-filter_threads','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],
        capture_output=True,timeout=14)
    return run.returncode==0 and len(run.stdout)==2304

def production_guard():
    with urllib.request.urlopen('http://192.0.2.20:8765/api/broadcast',timeout=8) as r:
        live=json.load(r)['playout'].get('output') or {}
    if not live.get('moving') or (live.get('measured_fps') or 0)<26:
        raise RuntimeError('Live output guard stopped the off-air test')
    return live.get('measured_fps')

def main():
    for _ in range(30):
        try:command('INFO 1',xml=True);break
        except OSError:time.sleep(1)
    server=Server(('127.0.0.1',8555),Proxy)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    p.command=command
    p.CAMERAS={name:{**dict(p.CAMERAS[name]),'rtsp':f'rtsp://127.0.0.1:8555/{name}'}
               for name in p.CAMERAS}
    report={'started_at':time.time(),'amcp_port':5351,'groups':[],
            'limits':'Temporary TCP loss/stall and controller recovery only; no corrupt-bitstream or full cold-boot claim.'}
    try:
        command('ADD 1-1 FILE "/workspace/media/fault-check.mp4" -codec:v h264_nvenc -preset:v p1 -b:v 2000k -an -format mp4')
        recording_start=time.monotonic()
        command('PLAY 1-10 route://2')
        for group in (['cam1','cam2','cam3','cam4'],[f'ntv-cam{i}' for i in range(1,5)]):
            row={'names':group,'samples':[],'decoded_probes':{}}
            report['groups'].append(row)
            policies={n:PicturePolicy() for n in group}
            for name in group:
                ok=independently_decoded(p.CAMERAS[name]['rtsp'])
                row['decoded_probes'][name]=ok
                if not ok:raise RuntimeError('No independent picture for '+name)
            for index,name in enumerate(group):
                ch=p.source_channel(name)
                image=Image.new('RGB',(640,360),'#10222b')
                ImageDraw.Draw(image).text((30,160),name.upper()+' / WAITING',fill='white',font_size=28)
                image.save(ROOT/(name+'.png'))
                command(f'PLAY {ch}-1 "/workspace/{name}.png"')
                p._slates.add(name)
                p.reload_camera(name)
                command(f'PLAY 2-{10+index} route://{ch}')
                command(f'MIXER 2-{10+index} FILL {(index%2)*.5} {(index//2)*.5} .5 .5')
            start=time.monotonic();phase='warm';all_live_at=None;restored_at=None
            while time.monotonic()-start<100:
                now=time.monotonic()
                sample={'elapsed':round(now-start,2),'mode':MODE,'cameras':{}}
                for name in group:
                    if name in p._loaded:
                        p.observe_sources(info(p.source_channel(name)),now,name)
                        p.retire_stalled_input(name,now)
                    age=now-p._changed[name] if name in p._changed else None
                    display=policies[name].update(now,p._last.get(name),age,name in p._loaded)
                    p.source_picture(name,display!='loading')
                    sample['cameras'][name]={'display':display,'loaded':name in p._loaded,
                        'decoded':p._last.get(name),'age':age}
                if len(row['samples'])%5==0:sample['program_fps']=production_guard()
                row['samples'].append(sample)
                states=[s['display'] for s in sample['cameras'].values()]
                if phase=='warm' and all(s=='live' for s in states):
                    all_live_at=now;phase='healthy'
                elif phase=='healthy' and now-all_live_at>=5:
                    mode('stalled');phase='stall';fault_at=now
                elif phase=='stall' and now-fault_at>=12:
                    assert all(s=='loading' for s in states),'Stale picture stayed visible'
                    assert not any(s['loaded'] for s in sample['cameras'].values()),'Dead decoder retained'
                    mode('closed');phase='closed';closed_at=now
                elif phase=='closed' and now-closed_at>=3:
                    mode('flowing');restored_at=now
                    for name in group:
                        assert independently_decoded(p.CAMERAS[name]['rtsp']),name
                    for name in group:
                        p.reload_camera(name)
                    phase='return'
                elif phase=='return' and all(s=='live' for s in states):
                    row['recovered_seconds']=round(now-restored_at,2)
                    # Keep the recovered composite on the test output long
                    # enough to record visible proof before clearing the bank.
                    time.sleep(3)
                    row['ready_capture_seconds']=round(time.monotonic()-recording_start,2)
                    production_guard()
                    time.sleep(3)
                    row['passed']=True;break
                time.sleep(.5)
            assert row.get('passed'),'Recovery deadline exceeded'
            for name in group:
                command(f'CLEAR {p.source_channel(name)}')
                p._loaded.discard(name)
            command('CLEAR 2')
        report['passed']=True
    finally:
        mode('closed');server.shutdown();server.server_close()
        try:command('REMOVE 1-1')
        except Exception:pass
        report['ended_at']=time.time()
        (ROOT/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':report['passed'],'groups':[
        {'names':r['names'],'recovered_seconds':r['recovered_seconds']} for r in report['groups']]}))

if __name__=='__main__':main()
