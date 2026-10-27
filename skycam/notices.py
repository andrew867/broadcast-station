"""Operator-reviewed community notices, with validity windows and revision checks."""
from datetime import datetime,timezone
import io,json,threading,uuid,time
from PIL import Image
from pydantic import Field,model_validator
from .models import StrictModel
from .rundown_library import LibraryConflict
from .storage import save_json

class Notice(StrictModel):
    id:str=Field(default_factory=lambda:uuid.uuid4().hex,pattern=r'^[a-f0-9]{32}$')
    title:str=Field(min_length=1,max_length=100)
    text:str=Field(default='',max_length=1600)
    image_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
    credit:str=Field(default='',max_length=120)
    location:str=Field(default='',max_length=100)
    starts_at:datetime|None=None
    ends_at:datetime|None=None
    approved:bool=False
    url:str=Field(default='',max_length=256)
    @model_validator(mode='after')
    def validate_content(self):
        if not self.title.strip() or (not self.text.strip() and not self.image_id):raise ValueError('Add a title and either a message or an image')
        for value in (self.starts_at,self.ends_at):
            if value and value.tzinfo is None:raise ValueError('Notice times must include a timezone')
        if self.starts_at and self.ends_at and self.ends_at<=self.starts_at:raise ValueError('End must follow start')
        if self.url:
            from urllib.parse import urlsplit
            parsed=urlsplit(self.url)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in self.url):raise ValueError('Use an http or https information link without credentials or spaces')
        return self
    def active(self,now):return self.approved and (self.starts_at is None or self.starts_at<=now) and (self.ends_at is None or now<self.ends_at)

class NoticeWrite(StrictModel):
    expected_revision:int=Field(ge=0)
    notice:Notice

class NoticeBoard:
    def __init__(self,data):
        self.assets=data/'notice-images';self.assets.mkdir(parents=True,exist_ok=True)
        self.path=data/'broadcast'/'notices.json';self.lock=threading.RLock();self.revision=0;self.items=[];self.error=None
        if self.path.exists():
            try:
                saved=json.loads(self.path.read_text(encoding='utf-8'));self.revision=int(saved['revision'])
                self.items=[Notice.model_validate(row) for row in saved['items']]
            except (ValueError,KeyError,TypeError,OSError):self.error='Saved notices could not be read. Restore their backup before editing.'
    def public(self,now=None):
        now=now or datetime.now(timezone.utc)
        with self.lock:return {'revision':self.revision,'error':self.error,'items':[{**n.model_dump(mode='json'),'active':n.active(now)} for n in self.items]}
    def active(self):return [r for r in self.public()['items'] if r['active']]
    def _commit(self,revision,items):
        if self.error:raise RuntimeError(self.error)
        if revision!=self.revision:raise LibraryConflict('Notices changed in another window. Reload before saving.')
        save_json(self.path,{'revision':revision+1,'items':[n.model_dump(mode='json') for n in items]})
        self.revision+=1;self.items=items
    def save(self,body):
        with self.lock:
            if body.notice.image_id and not (self.assets/(body.notice.image_id+'.png')).is_file():raise ValueError('Upload the notice image first')
            items=[n for n in self.items if n.id!=body.notice.id]+[body.notice]
            if len(items)>50:raise ValueError('The noticeboard holds up to 50 notices')
            self._commit(body.expected_revision,items);return self.public()
    def delete(self,id,revision):
        with self.lock:
            if not any(n.id==id for n in self.items):raise KeyError('Notice not found')
            self._commit(revision,[n for n in self.items if n.id!=id]);return self.public()

    def upload(self, raw):
        if not 0<len(raw)<=16*1024*1024:raise ValueError('Image must be smaller than 16 MiB')
        with self.lock:
            if len(list(self.assets.glob('*.png')))>=100:raise ValueError('Image library is full (100). Remove unused images before uploading more.')
            with Image.open(io.BytesIO(raw),formats=('PNG','JPEG','WEBP')) as im:
                if im.format not in ('PNG','JPEG','WEBP') or im.width>7680 or im.height>4320:raise ValueError('Choose PNG, JPEG or WebP, up to 7680 by 4320')
                im.load();image=im.convert('RGB');image.thumbnail((3840,2160))
            identifier=uuid.uuid4().hex;path=self.assets/(identifier+'.png');image.save(path,format='PNG',compress_level=3)
            return {'image_id':identifier,'width':image.width,'height':image.height,'url':'/api/notices/images/'+identifier}

    def image_path(self, identifier):
        if not identifier or len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):raise ValueError('Unknown image')
        path=self.assets/(identifier+'.png')
        if not path.is_file():raise ValueError('Image unavailable')
        return path

    def clean_unused(self):
        # Keep recent drafts in other browser tabs safe for at least 24 hours.
        with self.lock:
            if self.error:raise RuntimeError(self.error)
            used={n.image_id for n in self.items};removed=0
            for path in self.assets.glob('*.png'):
                if path.stem not in used and time.time()-path.stat().st_mtime>86400:
                    path.unlink();removed+=1
            return {'removed':removed,'note':'Saved notice images and uploads from the past 24 hours were kept.'}
