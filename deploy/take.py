"""Select a known live camera and matching graphics on the test channel."""
import json
import sys
import urllib.request
from amcp import command

camera=sys.argv[1] if len(sys.argv)>1 else 'cam4'
labels={'cam1':('STJ WEST','ST. JOHN’S, NL'),'cam2':('STJ NORTH','ST. JOHN’S, NL'),
        'cam3':('QUIDI VIDI LAKE','ST. JOHN’S, NL'),'cam4':('THE POST TAPHOUSE','TORBAY, NL')}
if camera not in labels:raise SystemExit('Choose cam1, cam2, cam3 or cam4')
print(command(f'PLAY 1-10 "rtmp://192.0.2.10/{camera}"'))
print(command('MIXER 1-10 FILL 0 0 1 1'))
with urllib.request.urlopen('http://127.0.0.1:8765/api/broadcast') as response:
    state=json.load(response)['state']
state['camera']=camera;state['location']=labels[camera][1]
request=urllib.request.Request('http://127.0.0.1:8765/api/broadcast',data=json.dumps(state).encode(),
    headers={'Content-Type':'application/json','X-Skycam-Edit':'1'},method='PUT')
with urllib.request.urlopen(request) as response:response.read()
print(command(f'PLAY 1-20 [HTML] "http://127.0.0.1:8765/broadcast?camera={camera}"'))
