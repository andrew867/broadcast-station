"""Isolated real-stream outage test. Never changes camera registry or MediaMTX.

Only an additional localhost reader is disconnected. Production readers are not
routed through this proxy. This does not prove full on-air or multi-camera recovery.
"""
import importlib.util,json,select,socket,threading,time,urllib.request
from pathlib import Path

spec=importlib.util.spec_from_file_location('source_health',Path(__file__).with_name('source-health.py'))
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
enabled=threading.Event();enabled.set();shutdown=threading.Event();stop=threading.Event();connections=set();lock=threading.Lock()

def forward(client):
    upstream=None
    try:
        if not enabled.is_set():return
        upstream=socket.create_connection(('192.0.2.10',8554),timeout=5)
        with lock:connections.update([client,upstream])
        while enabled.is_set() and not shutdown.is_set():
            ready,_,_=select.select([client,upstream],[],[],.5)
            for source in ready:
                data=source.recv(65536)
                if not data:return
                (upstream if source is client else client).sendall(data)
    except OSError:pass
    finally:
        for sock in [client,upstream]:
            if sock:
                with lock:connections.discard(sock)
                sock.close()

def serve(listener):
    while not shutdown.is_set():
        try:client,_=listener.accept()
        except socket.timeout:continue
        except OSError:return
        threading.Thread(target=forward,args=(client,),daemon=True).start()

def status():
    with reader.LOCK:return dict(reader.STATUS.get('isolated-cam3',{}))
def wait_ready(seconds):
    started=time.monotonic()
    while time.monotonic()-started<seconds:
        if status().get('ready'):return round(time.monotonic()-started,2)
        time.sleep(.5)
    raise RuntimeError('No decodable camera frame before deadline')

if __name__=='__main__':
    out=Path('/srv/station/data-web/acceptance/source-reconnect.json');out.parent.mkdir(exist_ok=True)
    report={'test':'Isolated cam3 RTSP connection, real VAAPI decoder','outage_seconds':90,'samples':[]}
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(.5)
    port=listener.getsockname()[1];threading.Thread(target=serve,args=(listener,),daemon=True).start()
    worker=threading.Thread(target=reader.worker,args=('isolated-cam3','cam3',stop,f'rtsp://127.0.0.1:{port}/cam3'),daemon=True);worker.start()
    try:
        report['initial_ready_seconds']=wait_ready(50);report['before']=status();enabled.clear()
        with lock:
            for connection in list(connections):
                try:connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
        start=time.monotonic()
        while time.monotonic()-start<90:
            row={'elapsed':round(time.monotonic()-start,2),'source':status()}
            try:
                with urllib.request.urlopen('http://127.0.0.1:8765/api/broadcast',timeout=5) as response:row['program']=json.load(response)['playout'].get('output')
            except Exception as exc:row['error']=str(exc)
            report['samples'].append(row);time.sleep(2)
        enabled.set();report['recovered_seconds']=wait_ready(60);report['after']=status()
        report['false_ready_after_grace']=any(r['source'].get('ready') for r in report['samples'] if r['elapsed']>5)
        report['program_stopped_samples']=sum(r.get('program',{}).get('moving') is False for r in report['samples'] if r.get('program'))
        report['passed']=not report['false_ready_after_grace'] and report['after']['generation']>report['before']['generation'] and report['program_stopped_samples']==0
    except Exception as exc:report.update(passed=False,error=str(exc))
    finally:
        enabled.clear();shutdown.set();stop.set();listener.close();worker.join(timeout=6)
        out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
