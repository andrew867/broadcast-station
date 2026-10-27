import json,os,socket,subprocess,sys,time,xml.etree.ElementTree as ET
import select,socketserver,threading
from pathlib import Path
root=Path('/srv/station/camera-fault-check-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()))
root.mkdir()
for name in ('media','logs','data','templates','runtime/camera-recovery'):(root/name).mkdir(parents=True)
gateway=subprocess.check_output(['docker','network','inspect','bridge','--format','{{(index .IPAM.Config 0).Gateway}}'],text=True).strip()
class Forward(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with socket.create_connection(('127.0.0.1',8555),3) as upstream:
                peers=[self.request,upstream]
                while True:
                    for source in select.select(peers,[],[],1)[0]:
                        data=source.recv(65536)
                        if not data:return
                        peers[1 if source is peers[0] else 0].sendall(data)
        except OSError:pass
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
server=Server((gateway,18555),Forward)
threading.Thread(target=server.serve_forever,daemon=True).start()
cfg=ET.parse('/srv/station/skycam/deploy/casparcg.config')
for channel in cfg.find('channels'):
    channel.find('video-mode').text='720p3000'
    for item in list(channel.find('consumers')):channel.find('consumers').remove(item)
for e in cfg.findall('.//tcp/port'):e.text='5351'
cfg.write(root/'casparcg.config')
auth=[line.split('=',1)[1] for line in subprocess.check_output(
    ['systemctl','--user','show-environment'],text=True).splitlines() if line.startswith('XAUTHORITY=')][0]
name='skycam-fault-engine-'+str(int(time.time()))
args=['docker','run','-d','--name',name,'--network','bridge','--device','nvidia.com/gpu=all',
      '--memory','2200m','--cpus','3','--pids-limit','768','--log-opt','max-size=5m','--log-opt','max-file=1',
      '--user',f'{os.getuid()}:{os.getgid()}','-e','DISPLAY=:0','-e','XAUTHORITY=/tmp/xauthority',
      '-v',auth+':/tmp/xauthority:ro','-v','/tmp/.X11-unix:/tmp/.X11-unix:ro',
      '-v',str(root)+':/workspace','skycam-caspar:2.5.1-idle-cache']
subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
try:
    test=['docker','run','--rm','--name',name+'-control','--network','container:'+name,'--memory','600m',
          '--cpus','1','--pids-limit','100','--user',f'{os.getuid()}:{os.getgid()}',
          '-e','SKYCAM_PLAYOUT=0','-e','SKYCAM_DATA=/settings','-e','TEST_HOST_GATEWAY='+gateway,
          '-e','OPENBLAS_NUM_THREADS=1','-e','PYTHONPATH=/app',
          '-v','/srv/station/data-web:/settings:ro',
          '-v','/srv/station/skycam:/app:ro','-v',str(root)+':/review',
          'skycam-web:local','python','/app/deploy/camera-fault-check.py']
    run=subprocess.run(test,timeout=330)
    print(json.dumps({'folder':str(root),'exit_code':run.returncode}))
finally:
    subprocess.run(['docker','stop','-t','5',name+'-control'],capture_output=True)
    subprocess.run(['docker','stop','-t','5',name],capture_output=True)
    server.shutdown();server.server_close()
    Path('/tmp/camera-fault-check-location.txt').write_text(str(root))


sys.exit(run.returncode)
