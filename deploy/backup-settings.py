"""Snapshot operator settings and verify a restore into an isolated folder."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import shutil
import sqlite3
from datetime import datetime, timezone

def backup(root):
    root=Path(root).resolve()
    candidates=list((root/'data-web').glob('*.json'))
    candidates+=list((root/'data-web/broadcast').glob('*.json'))
    candidates+=list((root/'data-web/broadcast/camera-revisions').glob('*.json'))
    candidates+=list((root/'data-web/revisions').glob('*.json'))
    candidates+=list((root/'data-web/commercial').glob('*.json'))
    candidates+=list((root/'data-web/broadcast/format-backups').glob('*.json'))
    candidates.append(root/'casparcg.config')
    payload={}
    for path in candidates:
        if not path.is_file() or path.is_symlink() or path.name=='source-health.json':continue
        data=path.read_bytes()
        if path.suffix=='.json':json.loads(data)
        payload[path.relative_to(root).as_posix()]=data
    history=root/'data-web/history/power.sqlite3'
    if history.is_file() and not history.is_symlink():
        with tempfile.TemporaryDirectory(prefix='power-backup-') as temporary:
            target=Path(temporary)/'power.sqlite3'
            with sqlite3.connect(history) as source,sqlite3.connect(target) as destination:
                source.backup(destination)
                if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Power history backup failed integrity check')
            payload['data-web/history/power.sqlite3']=target.read_bytes()
    if not payload:raise RuntimeError('No settings found; no backup created')
    digests={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}
    assets={p.relative_to(root).as_posix():p for p in (root/'data-web/commercial/assets').glob('*') if p.is_file() and not p.is_symlink() and p.suffix in ('.png','.mp4')}
    for folder in ('references','notice-images'):
        assets.update({p.relative_to(root).as_posix():p for p in (root/'data-web'/folder).glob('*') if p.is_file() and not p.is_symlink() and p.suffix in ('.png','.json')})
    for name,path in assets.items():
        with path.open('rb') as stream:digests[name]=hashlib.file_digest(stream,'sha256').hexdigest()
    folder=root/'backups';folder.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=folder/f'settings-{stamp}.tar.gz'
    with tarfile.open(target,'w:gz') as archive:
        for name,data in {**payload,'manifest.json':json.dumps(digests,indent=2).encode()}.items():
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
            archive.addfile(info,io.BytesIO(data))
        for name,path in assets.items():archive.add(path,arcname=name,recursive=False)
    os.chmod(target,0o600)
    # Restore only the known snapshot members, never production paths.
    with tempfile.TemporaryDirectory(prefix='skycam-restore-check-') as temporary:
        staging=Path(temporary)
        with tarfile.open(target,'r:gz') as archive:
            for name in digests:
                restored=staging/name;restored.parent.mkdir(parents=True,exist_ok=True)
                with restored.open('wb') as target_stream:shutil.copyfileobj(archive.extractfile(name),target_stream,1024*1024)
                with restored.open('rb') as source_stream:actual=hashlib.file_digest(source_stream,'sha256').hexdigest()
                if actual!=digests[name]:
                    raise RuntimeError(f'Restore verification failed: {name}')
    return {'archive':str(target),'files':len(digests),'isolated_restore_verified':True,
            'excludes':'Music files, generated pictures, map tiles, Docker images/containers and MediaMTX secrets are not included. Local advertising/sponsor assets are included.'}

if __name__=='__main__':print(json.dumps(backup('/srv/station'),indent=2))
