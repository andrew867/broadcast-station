# SPDX-License-Identifier: Apache-2.0
"""Create a small allowlisted support report without logs, URLs or credentials."""
import argparse,datetime,hashlib,json,math,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stationctl import compose


def read_object(home,relative):
    path=home/relative
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(home.resolve()) or path.stat().st_size>2_000_000:return {}
        value=json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}


def number(value):
    return value if type(value) in (int,float) and math.isfinite(value) else None


def build(home,output,runtime=False,gpu='nvidia'):
    home=Path(home).resolve();output=Path(output)
    config=read_object(home,'station.json');settings=config.get('output',{})
    if not isinstance(settings,dict):settings={}
    providers=config.get('providers',{})
    providers=providers if isinstance(providers,dict) else {}
    known=('adsb','metadata','news','weather','flights','markets','marine','ais','tides','outages','power','power_reports','alerts','radar')
    payload={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'schema_version':number(config.get('schema_version')),
        'profile':settings.get('profile') if settings.get('profile') in ('720p3000','720p6000','1080p3000','1080i5994','2160p3000','2160p6000') else None,
        'encoder':settings.get('encoder') if settings.get('encoder') in ('h264_nvenc','libx264') else None,
        'hdmi':settings.get('hdmi') is True,'desktop_audio':settings.get('desktop_audio') is True,
        'enabled_providers':[name for name in known if providers.get(name) is True],
        'excluded':'Raw logs, endpoints, location, names, credentials, music, pictures and accounting'}
    catalog=read_object(home,'data/broadcast/cameras.json').get('cameras',[])
    if not isinstance(catalog,list):catalog=[]
    payload['camera_counts']={'configured':len(catalog),'enabled':sum(isinstance(c,dict) and c.get('enabled') is True for c in catalog)}
    watchdog=read_object(home,'runtime/watchdog.json')
    payload['watchdog']={'checked_at':number(watchdog.get('checked_at')),'frame':number(watchdog.get('frame')),'recovery_enabled':watchdog.get('recovery_enabled') is True,'maintenance':watchdog.get('maintenance') is True}
    storage=read_object(home,'data/storage-health.json')
    payload['storage']={name:number(storage.get(name)) for name in ('at','cache_bytes','free_bytes','minimum_free_bytes')}
    if runtime:
        states={}
        for service in ('studio','engine','source-hub','source-health','maintenance'):
            try:
                ids=subprocess.check_output(compose(home,gpu)+['ps','-a','-q',service],stderr=subprocess.DEVNULL,text=True,timeout=10).split()
                if len(ids)!=1:states[service]={'available':False};continue
                template='{{json .State.Status}} {{.RestartCount}}'
                text=subprocess.check_output(['docker','inspect','--format='+template,ids[0]],stderr=subprocess.DEVNULL,text=True,timeout=10).strip()
                state,restarts=text.split()
                state=json.loads(state)
                states[service]={'state':state if state in ('created','running','paused','restarting','removing','exited','dead') else 'unknown','restarts':int(restarts)}
            except (OSError,ValueError,subprocess.SubprocessError):states[service]={'available':False}
        payload['services']=states
    data=(json.dumps(payload,indent=2)+'\n').encode()
    manifest=json.dumps({'report.json':hashlib.sha256(data).hexdigest()},indent=2).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('report.json',data);archive.writestr('manifest.json',manifest)
    return {'archive':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'files':2}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('home',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--runtime',action='store_true');parser.add_argument('--gpu',choices=['nvidia','intel'],default='nvidia');args=parser.parse_args()
    print(json.dumps(build(args.home,args.output,args.runtime,args.gpu),indent=2))
