"""Bounded, restart-safe still histories. Times describe receipt, never radar observation."""
import hashlib
import io
import json
import math
import re
import threading
import time
from pathlib import Path
from PIL import Image


class PictureHistory:
    def __init__(self, folder, count=120, age=7200, budget=24*1024*1024):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.count=count;self.age=age;self.budget=budget;self.lock=threading.RLock()
        self.index=self.folder/'index.json'
        try:saved=json.loads(self.index.read_text())
        except (OSError,ValueError):saved=[]
        self.rows=[];seen=set()
        for row in saved if isinstance(saved,list) else []:
            if not isinstance(row,dict):continue
            at=row.get('at');name=row.get('file');digest=row.get('digest')
            if (type(at) not in (int,float) or not math.isfinite(at) or
                not isinstance(name,str) or not re.fullmatch(r'[0-9]+-[a-f0-9]{12}\.jpg',name) or
                not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest) or
                name in seen):continue
            path=self.folder/name
            if path.is_symlink() or not path.is_file():continue
            self.rows.append({'at':at,'file':name,'digest':digest});seen.add(name)
        self.prune()
        if saved!=self.rows:self.save()
        known={r['file'] for r in self.rows}
        for path in self.folder.glob('*.jpg'):
            if path.name not in known:path.unlink(missing_ok=True)

    def save(self):
        temp=self.index.with_suffix('.tmp');temp.write_text(json.dumps(self.rows));temp.replace(self.index)

    def prune(self, now=None):
        with self.lock:
            now=time.time() if now is None else now
            keep=[r for r in self.rows if 0<=now-r['at']<=self.age and (self.folder/r['file']).exists()]
            keep=sorted(keep,key=lambda r:r['at'])[-self.count:]
            total=sum((self.folder/r['file']).stat().st_size for r in keep)
            while keep and total>self.budget:
                row=keep.pop(0);total-=(self.folder/row['file']).stat().st_size
            names={r['file'] for r in keep}
            for row in self.rows:
                if row['file'] not in names:(self.folder/row['file']).unlink(missing_ok=True)
            changed=keep!=self.rows;self.rows=keep
            if changed:self.save()

    def add(self, content, at=None, deduplicate=False):
        at=time.time() if at is None else at
        if not 0<=time.time()-at<=self.age:raise ValueError('History timestamp is outside retention window')
        if len(content)>8_000_000:raise ValueError('History image exceeds input limit')
        digest=hashlib.sha256(content).hexdigest()
        with self.lock:
            self.prune()
            if self.rows and (at<=self.rows[-1]['at'] or (deduplicate and digest==self.rows[-1]['digest'])):return False
            with Image.open(io.BytesIO(content),formats=('PNG','JPEG')) as im:
                if im.width*im.height>16_000_000:raise ValueError('History image dimensions exceed limit')
                im=im.convert('RGB');im.thumbnail((960,540));out=io.BytesIO();im.save(out,format='JPEG',quality=88)
            content=out.getvalue()
            if len(content)>self.budget:raise ValueError('History image exceeds storage budget')
            name=f'{int(at*1000)}-{digest[:12]}.jpg';path=self.folder/name
            temp=path.with_suffix('.tmp');temp.write_bytes(content);temp.replace(path)
            self.rows.append({'at':at,'file':name,'digest':digest})
            self.prune();self.save();return True

    def entries(self):
        with self.lock:
            self.prune();return [dict(r) for r in self.rows]

    def frame(self, index):
        with self.lock:
            rows=self.entries()
            while rows:
                row=rows[index%len(rows)];path=self.folder/row['file']
                try:
                    with Image.open(path) as im:
                        if im.width*im.height>960*540:raise ValueError('Invalid stored history dimensions')
                        return im.convert('RGB'),row
                except (OSError,ValueError,Image.DecompressionBombError):
                    # A partial/corrupt local JPEG must not pin replay forever.
                    path.unlink(missing_ok=True)
                    self.rows=[r for r in self.rows if r['file']!=row['file']]
                    self.save();rows=self.entries()
            return None,None

    def public(self):
        rows=self.entries()
        return {'frames':len(rows),'first_at':rows[0]['at'] if rows else None,'last_at':rows[-1]['at'] if rows else None,
                'max_frames':self.count,'max_age_s':self.age,'max_bytes':self.budget}

    def discard_oldest(self):
        with self.lock:
            if self.rows:
                (self.folder/self.rows.pop(0)['file']).unlink(missing_ok=True);self.save()


def enforce_budget(histories, budget):
    """Also cap the combined archive across retired and newly created camera IDs."""
    rows=[];total=0
    for history in histories:
        for row in history.entries():
            size=(history.folder/row['file']).stat().st_size
            total+=size;rows.append((row['at'],size,history))
    for _,size,history in sorted(rows,key=lambda r:r[0]):
        if total<=budget:break
        history.discard_oldest();total-=size
