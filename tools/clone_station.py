# SPDX-License-Identifier: Apache-2.0
"""Create an inactive standby from a verified current-format station snapshot."""
import argparse,hashlib,json,os,re,tarfile
from pathlib import Path,PurePosixPath

RUNTIME={'source-health.json','storage-health.json','source-events.json','watchdog-history.json',
         'alert-presentation-history.json','program-clock-history.json','rundown-intent.json'}

def read_snapshot(path,expected_sha256):
    if not re.fullmatch('[0-9a-f]{64}',expected_sha256):raise ValueError('Expected SHA256 required')
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected_sha256:raise ValueError('Snapshot SHA256 mismatch')
    files={};total=0
    with tarfile.open(path,'r:gz') as archive:
        for member in archive:
            name=member.name;p=PurePosixPath(name);total+=member.size
            if (not member.isfile() or p.is_absolute() or p.as_posix()!=name or '..' in p.parts or '\\' in name or ':' in name
                or name in files or len(files)>=10000 or total>512*1024**2):raise ValueError('Unsafe snapshot member')
            if p.suffix.lower() in {'.key','.pem','.p12','.pfx'} or (p.suffix.lower()=='.env' and name!='compose.env'):raise ValueError('Credentials are not standby settings')
            files[name]=archive.extractfile(member).read()
    manifest=json.loads(files.pop('manifest.json'))
    if set(manifest)!=set(files):raise ValueError('Snapshot manifest mismatch')
    for name,data in files.items():
        if hashlib.sha256(data).hexdigest()!=manifest[name]:raise ValueError('Snapshot payload hash mismatch')
        if b'PRIVATE KEY-----' in data:raise ValueError('Private key in snapshot')
    return files

def clone(snapshot,destination,sha256,cameras=()):
    destination=Path(destination)
    if destination.exists():raise ValueError('Standby destination must not exist')
    files=read_snapshot(snapshot,sha256)
    config=json.loads(files['station.json'])
    if config.get('schema_version')!=1:raise ValueError('Unsupported station schema')
    inventory=json.loads(files['data/broadcast/cameras.json'])
    ids={c['id'] for c in inventory['cameras']}
    if not set(cameras)<=ids:raise ValueError('Unknown standby camera')
    # Never inherit a publisher destination, native control address or keys.
    config['output'].update(profile='1080p3000',encoder='libx264',bitrate_kbps=8000,
        playout=False,publish=False,publish_url='',hdmi=False,desktop_audio=False,
        amcp_host='engine',amcp_port=5250,studio_url='http://studio:8765',screen=0,screen_rect=[0,0,1920,1080])
    config.update(secrets={},data_directory='/workspace/data-web',music_directory='/workspace/media/music',
        brand_file='/station/branding.json',secrets_directory='/station/secrets')
    config['providers']={key:False for key in config['providers']}
    payload={name:data for name,data in files.items() if
        (name=='branding.json' or name.startswith(('data/','accounting/','branding-assets/')))
        and not any(part in ('runtime','cache','secrets') for part in PurePosixPath(name).parts)
        and PurePosixPath(name).name not in RUNTIME and not name.endswith('-cache.json')}
    for row in inventory['cameras']:row['enabled']=row['id'] in cameras
    def save(name,value):payload[name]=json.dumps(value,indent=2).encode()+b'\n'
    save('station.json',config);save('data/broadcast/cameras.json',inventory)
    for name in ('rundown.json','program-clock.json','state.json'):
        key='data/broadcast/'+name
        if key not in payload:continue
        payload['standby-original/'+name]=payload[key]
        value=json.loads(payload[key])
        if name=='rundown.json':value['resume_after_restart']=False
        elif name=='program-clock.json':value['config']['enabled']=False
        elif cameras:value['camera']=cameras[0]
        save(key,value)
    save('data/broadcast/rundown-intent.json',{'running':False,'index':0})
    save('data/broadcast/source-routing.json',{'shared_camera_inputs':True})
    policy='accounting/aeroapi/policy.json'
    if policy in payload:
        value=json.loads(payload[policy]);value['enabled']=False;save(policy,value)
    report={'source_sha256':sha256,'files_copied':len(payload),'cameras_enabled':list(cameras),
        'outputs_enabled':False,'providers_enabled':False,'credentials_copied':False,
        'accounting':'Historical ledger retained; requests disabled. Reconcile active account use before promotion.',
        'music':'Settings retained; external music files and generated cache are not in this snapshot.',
        'role':'Inactive standby, manual commissioning required'}
    save('standby-import.json',report)
    destination.mkdir(parents=True,exist_ok=False)
    if os.name!='nt':destination.chmod(0o700)
    for name,data in payload.items():
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        if os.name!='nt':path.chmod(0o600)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--sha256',required=True);p.add_argument('--camera',action='append',default=[]);a=p.parse_args()
    print(json.dumps(clone(a.snapshot,a.destination,a.sha256,a.camera),indent=2))
