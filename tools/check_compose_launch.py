# SPDX-License-Identifier: Apache-2.0
"""Launch the real full-station controller with no engine, feeds, GPU or outbound network."""
import argparse,json,os,subprocess,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stationctl import prepare


def check(image):
    with tempfile.TemporaryDirectory(prefix='station-compose-') as folder:
        home=prepare(Path(folder)/'station')
        config=json.loads((home/'station.json').read_text());config['output']['playout']=True
        (home/'station.json').write_text(json.dumps(config))
        (home/'display.xauthority').touch()
        override=Path(folder)/'test.json'
        override.write_text(json.dumps({'services':{s:{'image':image,'cpus':1,'mem_limit':'2g'} for s in ('studio','validate')},'networks':{'default':{'internal':True}}}))
        environment={**os.environ,'STATION_HOME':str(home),'STATION_UID':str(os.getuid()),'STATION_GID':str(os.getgid()),'DISPLAY':':99','STATION_XAUTHORITY':str(home/'display.xauthority'),'STATION_HTTP_PORT':'0','STATION_AMCP_PORT':'0'}
        command=['docker','compose','-p','station-launch-'+uuid.uuid4().hex[:10],'-f',str(ROOT/'compose.station.yaml'),'-f',str(override)]
        def run(args,timeout=60):return subprocess.check_output(command+args,env=environment,stderr=subprocess.STDOUT,text=True,timeout=timeout)
        try:
            run(['run','--rm','--no-deps','--pull','never','validate'])
            run(['up','-d','--no-build','--pull','never','studio'])
            deadline=time.monotonic()+90
            while True:
                try:
                    # Internal-only Docker networks need no host-published port.
                    raw=run(['exec','-T','studio','python','-c',"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8765/api/broadcast',timeout=3).read().decode())"],timeout=10)
                    payload=json.loads(raw)
                    break
                except (OSError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
                    if time.monotonic()>deadline:raise RuntimeError('Candidate controller did not become available')
                    time.sleep(1)
            assert payload['playout_enabled'] is True and payload['playout']['enabled'] is True,'Full-station launch inherited preview-only mode'
            assert not payload['playout']['connected'],'No engine should be present in this check'
            assert (home/'casparcg.config').is_file()
            result={'passed':True,'real_compose_mounts':True,'playout_enabled':True,'engine_started':False,'gpu_used':False,'outbound_network':False,'scope':'Full-station container startup only, not rendered output'}
            print(json.dumps(result,indent=2));return result
        finally:run(['down','--timeout','5'],timeout=45)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('image');args=parser.parse_args();check(args.image)
