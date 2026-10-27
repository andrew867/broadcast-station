"""Operator-requested native stills; never starts another continuous decoder."""
import json
from pathlib import Path
import threading
import time
import uuid
import re
from PIL import Image
from . import playout

class SnapshotBusy(ValueError):pass

class RenderedPreview:
    def __init__(self,data):
        self.folder=Path(data)/'runtime'/'confidence-stills';self.folder.mkdir(parents=True,exist_ok=True)
        self.lock=threading.Lock();self.last=-100.0

    def identity(self,kind):
        if kind=='program':return (1,playout._camera,playout._bank)
        if kind=='preview':
            prepared=playout._prepared
            if not prepared:raise SnapshotBusy('No scene is currently prepared. Prepare one in Studio first.')
            return (prepared['bank'],prepared['camera'],prepared['at'])
        raise ValueError('Choose program or preview')

    def capture(self,kind):
        if not playout.ENABLED:raise SnapshotBusy('Native snapshots are available on the broadcast host.')
        if not self.lock.acquire(blocking=False):raise SnapshotBusy('Another snapshot is being captured.')
        raw=None
        try:
            # A delayed native PRINT can arrive after a timed-out request. Bound
            # those abandoned UHD PNGs on the next request, without touching a
            # recent in-flight print or anything outside this scratch directory.
            for abandoned in self.folder.glob('raw-*.png'):
                if (not abandoned.is_symlink() and re.fullmatch(r'raw-[a-f0-9]{32}\.png',abandoned.name)
                        and time.time()-abandoned.stat().st_mtime>30):
                    abandoned.unlink(missing_ok=True)
            if time.monotonic()-self.last<10:raise SnapshotBusy('Wait ten seconds between native snapshots.')
            # Routine health polling also holds this lock. Give a short poll
            # time to finish instead of rejecting otherwise safe manual stills.
            if not playout.LOCK.acquire(timeout=.75):raise SnapshotBusy('A scene operation is in progress. Try again shortly.')
            try:
                if not playout.STATUS.get('ready'):raise SnapshotBusy('The playout engine is reconnecting.')
                identity=self.identity(kind);token=uuid.uuid4().hex
                raw=self.folder/('raw-'+token+'.png')
                # PRINT resolves filenames relative to /workspace/media, not as absolute paths.
                playout.command(f'PRINT {identity[0]} '+json.dumps('../runtime/confidence-stills/raw-'+token))
                self.last=time.monotonic();at=time.time()
            finally:playout.LOCK.release()
            deadline=time.monotonic()+4;picture=None
            while time.monotonic()<deadline:
                try:
                    with Image.open(raw) as image:
                        if image.width*image.height>3840*2160:raise ValueError('Snapshot exceeds program dimensions')
                        image.load();picture=image.convert('RGB')
                    break
                except (OSError,ValueError):time.sleep(.05)
            if picture is None:raise SnapshotBusy('The native still did not finish in time. Program is unchanged.')
            if not playout.LOCK.acquire(timeout=.75):raise SnapshotBusy('Scene changed while capturing. Try again.')
            try:
                if self.identity(kind)!=identity:raise SnapshotBusy('Scene changed while capturing. Try again.')
            finally:playout.LOCK.release()
            picture.thumbnail((1280,720),Image.Resampling.LANCZOS)
            target=self.folder/(token+'.jpg');picture.save(target,quality=86)
            for old in sorted(self.folder.glob('*.jpg'),key=lambda p:p.stat().st_mtime)[:-8]:old.unlink(missing_ok=True)
            return {'kind':kind,'scene':identity[1],'channel':identity[0],'at':at,
                'url':'/api/confidence/rendered/'+token+'.jpg',
                'note':'Native composited still, reduced to 720p. Preview excludes the separate program ticker and emergency bar.'}
        finally:
            if raw:raw.unlink(missing_ok=True)
            self.lock.release()

    def file(self,name):
        import re
        if not re.fullmatch(r'[a-f0-9]{32}\.jpg',name):raise ValueError('Invalid snapshot name')
        path=self.folder/name
        if not path.is_file():raise FileNotFoundError('Snapshot expired; capture another')
        return path
