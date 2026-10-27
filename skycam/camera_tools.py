"""On-demand probing and calibration stills, never another continuous decoder."""
import io
import json
import subprocess
import threading
import time
from fractions import Fraction
from PIL import Image
from .storage import save_json


class CameraTools:
    def __init__(self,data,catalog):
        self.folder=data/'references';self.folder.mkdir(parents=True,exist_ok=True)
        self.catalog=catalog;self.lock=threading.Lock()

    def source(self,camera):
        row=self.catalog.cameras.get(camera)
        if not row:raise ValueError('Unknown camera')
        if not row['enabled']:raise ValueError('Enable the camera before probing or capturing')
        return dict(row)

    def probe(self,camera):
        row=self.source(camera)
        if not self.lock.acquire(blocking=False):raise ValueError('A camera inspection is already running; try again shortly')
        try:
            result=subprocess.run(['ffprobe','-v','error','-rtsp_transport','tcp','-timeout','6000000',
                '-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,avg_frame_rate',
                '-of','json',row['rtsp']],capture_output=True,timeout=10,check=True)
            streams=json.loads(result.stdout).get('streams',[])
            if not streams:raise ValueError('No video stream was reported')
            stream=streams[0];w=int(stream['width']);h=int(stream['height'])
            if not 320<=w<=7680 or not 240<=h<=4320:raise ValueError('Unsupported source dimensions')
            rate=None
            for key in ('avg_frame_rate','r_frame_rate'):
                try:
                    f=float(Fraction(stream.get(key,'0/0')))
                    if 0<f<=240:rate=f;break
                except (ValueError,ZeroDivisionError):pass
            return {'camera':camera,'width':w,'height':h,'fps':rate,'codec':stream.get('codec_name'),
                    'checked_at':time.time(),'note':'Stream metadata, not measured decoded frame rate. Apply dimensions with Save camera.'}
        finally:self.lock.release()

    def capture(self,camera):
        row=self.source(camera)
        if not self.lock.acquire(blocking=False):raise ValueError('A camera inspection is already running; try again shortly')
        try:
            began=time.time()
            result=subprocess.run(['ffmpeg','-v','warning','-nostdin','-threads','1','-rtsp_transport','tcp',
                '-timeout','6000000','-err_detect','explode','-i',row['rtsp'],'-an','-frames:v','1',
                '-threads','1','-f','image2pipe','-c:v','png','pipe:1'],capture_output=True,timeout=12,check=True)
            errors=result.stderr.decode('utf-8',errors='replace').lower()
            if any(x in errors for x in ('corrupt','conceal','error','invalid','missed')):
                raise ValueError('Decoder reported damage; no calibration image was saved')
            return self.store(camera,result.stdout,'live capture',began)
        finally:self.lock.release()

    def store(self,camera,raw,origin='uploaded reference',captured_at=None):
        row=self.catalog.cameras.get(camera)
        if not row:raise ValueError('Unknown camera')
        if not 0<len(raw)<=16*1024*1024:raise ValueError('Choose an image smaller than 16 MiB')
        with Image.open(io.BytesIO(raw),formats=('PNG','JPEG','WEBP')) as im:
            if im.format not in ('PNG','JPEG','WEBP') or im.width>7680 or im.height>4320:
                raise ValueError('Use a PNG, JPEG or WebP no larger than 7680 by 4320')
            if im.size!=(row['width'],row['height']):
                raise ValueError(f"Image is {im.width} by {im.height}; set the camera dimensions to match before saving this reference")
            im.load();image=im.convert('RGB')
        name=f"reference-{camera}-{time.time_ns()}.png";path=self.folder/name
        image.save(path,format='PNG',compress_level=3)
        metadata={'camera':camera,'width':image.width,'height':image.height,'origin':origin,
                  'captured_at':captured_at,'saved_at':time.time(),'media_path':row['media_path'],
                  'note':'Capture checks decoder-reported damage. It cannot prove the upstream picture is current or visually undamaged.'}
        save_json(path.with_suffix('.json'),metadata)
        with self.catalog.lock:
            current=self.catalog.cameras.get(camera)
            if not current or any(current[k]!=row[k] for k in ('width','height','media_path')):
                path.unlink(missing_ok=True);path.with_suffix('.json').unlink(missing_ok=True)
                raise ValueError('Camera changed while saving; try again')
            self.catalog._write({**self.catalog.cameras,camera:{**current,'reference':name}},dict(self.catalog.quads),self.catalog.retired)
        # Retain a bounded reference history. Existing calibration points are
        # untouched because the geometry and native dimensions did not change.
        for old in sorted(self.folder.glob(f'reference-{camera}-*.png'),key=lambda p:p.stat().st_mtime)[:-8]:
            old.unlink(missing_ok=True);old.with_suffix('.json').unlink(missing_ok=True)
        return {**metadata,'reference':name,'url':'/samples/'+name}
