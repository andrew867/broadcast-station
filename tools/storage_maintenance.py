# SPDX-License-Identifier: Apache-2.0
"""Bound expendable picture caches; never delete settings, media or accounting."""
from pathlib import Path
import argparse,json,os,shutil,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skycam.station_config import CONFIG,bootstrap


def candidates(root):
    root=Path(root).resolve()
    for folder,pattern in [('map','tile-*.png')]:
        base=root/folder
        if not base.exists() or any(p.is_symlink() for p in [base,*base.parents] if p!=root.parent):continue
        for file in base.rglob(pattern):
            if file.is_symlink() or not file.is_file():continue
            resolved=file.resolve()
            if not resolved.is_relative_to(base.resolve()):continue
            try:stat=file.stat()
            except OSError:continue
            yield file,stat.st_mtime,stat.st_size


def maintain(root,cache_bytes,history_days,minimum_free,now=None):
    root=Path(root);now=time.time() if now is None else now
    rows=sorted(candidates(root),key=lambda r:r[1]);total=sum(r[2] for r in rows);removed=0;freed=0
    for path,stamp,size in rows:
        if stamp>now-300:continue # Never touch pictures still being written or selected.
        if total<=cache_bytes and stamp>=now-history_days*86400:continue
        try:path.unlink()
        except OSError:continue
        total-=size;removed+=1;freed+=size
        if removed>=2000:break
    free=shutil.disk_usage(root).free
    return {'at':now,'cache_bytes':total,'files_removed':removed,'bytes_reclaimed':freed,
            'free_bytes':free,'low_space':free<minimum_free,'minimum_free_bytes':minimum_free,
            'scope':'Map tiles only; indexed histories retain their own count, age and size bounds'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');args=parser.parse_args()
    bootstrap();root=Path(os.environ['SKYCAM_DATA']);root.mkdir(parents=True,exist_ok=True)
    while True:
        status=maintain(root,CONFIG.storage.cache_mib*1048576,CONFIG.storage.history_days,CONFIG.storage.minimum_free_mib*1048576)
        path=root/'storage-health.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(status));tmp.replace(path)
        if not args.watch:print(json.dumps(status));return
        time.sleep(300)

if __name__=='__main__':main()
