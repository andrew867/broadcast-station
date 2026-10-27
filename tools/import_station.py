# SPDX-License-Identifier: Apache-2.0
"""Import a verified legacy snapshot into a new, offline station directory."""
import argparse
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skycam.station_config import StationConfig,load
from skycam.radar_calibration import load_calibration

MAX_FILES=10000
MAX_BYTES=512*1024*1024


def snapshot(path):
    payload={};total=0
    with tarfile.open(path,'r:gz') as archive:
        for member in archive:
            name=member.name;p=PurePosixPath(name)
            if (not member.isfile() or p.is_absolute() or '..' in p.parts or '\\' in name
                or ':' in name or name in payload or len(payload)>=MAX_FILES):
                raise ValueError('Unsafe or duplicate snapshot member')
            total+=member.size
            if total>MAX_BYTES:raise ValueError('Snapshot exceeds import size limit')
            payload[name]=archive.extractfile(member).read()
    manifest=json.loads(payload.pop('manifest.json'))
    if not isinstance(manifest,dict) or set(manifest)!=set(payload):raise ValueError('Snapshot manifest does not match its files')
    for name,data in payload.items():
        if hashlib.sha256(data).hexdigest()!=manifest[name]:raise ValueError('Snapshot hash mismatch')
        if not (name.startswith('data-web/') or name=='casparcg.config'):raise ValueError('Unknown snapshot root')
        if PurePosixPath(name).suffix in ('.key','.pem','.env','.p12','.pfx'):raise ValueError('Credential file is not an operator setting')
        if b'PRIVATE KEY-----' in data:raise ValueError('Private key found in snapshot')
        if name.endswith('.json'):
            json.loads(data)
    return payload,manifest


def plan(archive,deployment=None):
    payload,manifest=snapshot(archive)
    config=deployment or StationConfig()
    config=config.model_copy(deep=True)
    if 'casparcg.config' in payload:
        mode=ET.fromstring(payload['casparcg.config']).findtext('./channels/channel/video-mode')
        config.output.profile=mode
        config=StationConfig.model_validate(config.model_dump())
    config.output.playout=False;config.output.publish=False;config.output.hdmi=False
    config.providers={key:False for key in config.providers}
    config.data_directory='data';config.music_directory='music';config.secrets_directory='secrets'
    copied={};excluded=[]
    for name,data in payload.items():
        if name=='casparcg.config':continue
        rel=PurePosixPath(name).relative_to('data-web')
        if (any(x in {'runtime','cache','source-health.json','performance-history'} for x in rel.parts)
            or rel.name.endswith('-cache.json') or rel.name in {'camera-transport.json','source-events.json','watchdog-history.json','alert-presentation-history.json','program-clock-history.json'}):
            excluded.append(name);continue
        copied['data/'+rel.as_posix()]=data
    camera_doc=json.loads(copied.get('data/broadcast/cameras.json',b'{"cameras":[]}'))
    camera_ids={row['id'] for row in camera_doc['cameras']}
    quad_ids=set(camera_doc.get('quads',{}))
    for members in camera_doc.get('quads',{}).values():
        if len(members)!=4 or len(set(members))!=4 or set(members)-camera_ids:raise ValueError('Invalid quad membership in snapshot')
    missing=[]
    for camera in camera_doc['cameras']:
        ref=camera.get('reference','')
        if ref and 'data/references/'+ref not in copied:missing.append({'camera_id':camera['id'],'kind':'reference image'})
    report={'format':'station-import-report','version':1,'snapshot_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
            'source_files_verified':len(manifest),'copied_files':len(copied),'copied_bytes':sum(map(len,copied.values())),
            'camera_count':len(camera_ids),'quad_count':len(quad_ids),'profile':config.output.profile,
            'disabled_cameras':[r['id'] for r in camera_doc['cameras'] if not r.get('enabled',True)],
            'excluded_runtime_files':excluded,'missing_assets':missing,
            'required_secret_roles':sorted(config.secrets),'offline_rehearsal':True,
            'safety_overrides':['playout disabled','publishing disabled','HDMI disabled','provider tasks disabled'],
            'preserved':'Operator settings, calibration, media and history copied byte-for-byte; no runtime process state imported',
            'pending':['Supply private secret files separately','Check missing references and operator music','Reconcile paid API accounting before enabling requests','Commission provider permissions and alert trust before enabling']}
    return config,copied,report


def import_snapshot(archive,destination,deployment=None,aeroapi_state=None,dry_run=False,references=None,radar_calibration=None):
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Destination already exists; import never overwrites a station')
    config,copied,report=plan(archive,deployment)
    if references:
        folder=Path(references).resolve();retained=[]
        cameras=json.loads(copied.get('data/broadcast/cameras.json',b'{"cameras":[]}'))['cameras']
        for row in cameras:
            name=row.get('reference','')
            if not name:continue
            if Path(name).name!=name or '\\' in name or name in ('.','..'):raise ValueError('Invalid reference filename')
            path=folder/name
            if path.is_symlink() or path.resolve().parent!=folder:raise ValueError('Reference outside its directory')
            if path.is_file():
                if path.stat().st_size>16*1024*1024:raise ValueError('Reference exceeds 16 MiB')
                copied['data/references/'+name]=path.read_bytes();retained.append(row['id'])
        report['missing_assets']=[item for item in report['missing_assets'] if item['camera_id'] not in retained]
        report['reference_images_copied']=len(retained)
        report['copied_files']=len(copied);report['copied_bytes']=sum(map(len,copied.values()))
    if radar_calibration:
        folder=Path(radar_calibration).resolve()
        for kind in ('east','island'):
            load_calibration(folder,kind)
            for name in (kind+'.json',kind+'-reference.jpg'):
                copied['data/radar/calibration/'+name]=(folder/name).read_bytes()
    report['radar_calibrations_copied']=[kind for kind in ('east','island')
        if all('data/radar/calibration/'+name in copied for name in (kind+'.json',kind+'-reference.jpg'))]
    for kind in ('east','island'):
        if kind not in report['radar_calibrations_copied']:
            report['missing_assets'].append({'radar':kind,'kind':'radar calibration and reference picture'})
    report['copied_files']=len(copied);report['copied_bytes']=sum(map(len,copied.values()))
    if dry_run:return report
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.station-import-',dir=destination.parent))
    try:
        for name,data in copied.items():
            target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        (stage/'station.json').write_text(config.model_dump_json(indent=2),encoding='utf-8')
        for name in ('music','secrets'): (stage/name).mkdir(mode=0o700)
        if aeroapi_state:
            source=Path(aeroapi_state).resolve();target=stage/'accounting/aeroapi';target.mkdir(parents=True)
            policy=source/'policy.json';ledger=source/'usage.sqlite'
            if policy.is_symlink() or ledger.is_symlink():raise ValueError('Accounting files cannot be symlinks')
            json.loads(policy.read_text());shutil.copy2(policy,target/'policy.json')
            with closing(sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True)) as db,closing(sqlite3.connect(target/'usage.sqlite')) as out:
                db.backup(out)
                out.commit()
                if out.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid accounting ledger')
            report['accounting_preserved']=True
        digests={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in copied}
        if any(digests[name]!=hashlib.sha256(data).hexdigest() for name,data in copied.items()):raise ValueError('Imported payload differs')
        report['semantic_diff']={'changed_operator_files':[],'missing_operator_files':[],'new_deployment_file':'station.json'}
        (stage/'import-report.json').write_text(json.dumps(report,indent=2))
        (stage/'import-manifest.json').write_text(json.dumps(digests,indent=2))
        # Protect copied private configuration and accounting, not just secret names.
        if os.name!='nt':
            for path in stage.rglob('*'):os.chmod(path,0o700 if path.is_dir() else 0o600)
        stage.rename(destination)
    except BaseException:
        # Only the freshly created sibling staging directory is ever removed.
        if stage.exists():
            if stage.resolve().parent!=destination.parent or not stage.name.startswith('.station-import-'):
                raise RuntimeError('Unexpected staging directory; refusing cleanup')
            shutil.rmtree(stage)
        raise
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path);parser.add_argument('destination',type=Path)
    parser.add_argument('--deployment',type=Path);parser.add_argument('--aeroapi-state',type=Path)
    parser.add_argument('--references',type=Path)
    parser.add_argument('--radar-calibration',type=Path,help='Directory containing paired east/island models and reference pictures')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        report=import_snapshot(args.snapshot,args.destination,load(args.deployment) if args.deployment else None,args.aeroapi_state,args.dry_run,args.references,args.radar_calibration)
        print(json.dumps(report,indent=2))
    except (ValueError,OSError,KeyError,ET.ParseError) as error:
        print('Import failed: '+type(error).__name__+'. Source files were not modified.',file=sys.stderr);raise SystemExit(2)
