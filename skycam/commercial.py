"""Local, reviewed advertising assets and an optional independent sponsor plate."""
import asyncio,hashlib,json,math,threading,time,uuid,os
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal
from PIL import Image,ImageDraw,ImageOps
from pydantic import Field,model_validator
from .models import StrictModel
from .storage import save_json
from .rundown_library import LibraryConflict
from .graphics import font,fit,brand,PAPER
from .image_cache import valid_image

MAX_UPLOAD=100*1024*1024
class Window(StrictModel):
    enabled:bool=False
    asset_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
    starts_at:datetime|None=None
    ends_at:datetime|None=None
    @model_validator(mode='after')
    def dates(self):
        for d in (self.starts_at,self.ends_at):
            if d and not d.tzinfo:raise ValueError('Dates must include a timezone')
        if self.starts_at and self.ends_at and self.starts_at>=self.ends_at:raise ValueError('End must follow start')
        return self
    def active(self,now):return self.enabled and (not self.starts_at or self.starts_at<=now) and (not self.ends_at or now<self.ends_at)
class Advertisement(Window):
    show_ticker:bool=True
    show_brand:bool=True
    end_policy:Literal['hold','loop']='hold'
    hold_seconds:int=Field(default=30,ge=5,le=180)
    background_color:str=Field(default='#0e1e29',pattern=r'^#[0-9a-fA-F]{6}$')
    background_asset_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
class Sponsor(Window):
    text:str=Field(default='SUPPORTED BY',max_length=45)
    scenes:list[str]=Field(default_factory=lambda:['cam1','cam2','cam3','cam4'],max_length=40)
    position:Literal['left','right']='left'
class CommercialConfig(StrictModel):
    advertisement:Advertisement=Field(default_factory=Advertisement)
    sponsor:Sponsor=Field(default_factory=Sponsor)
class CommercialWrite(StrictModel):
    expected_revision:int=Field(ge=0)
    config:CommercialConfig

class Commercial:
    def __init__(self,data):
        self.data=Path(data);self.folder=self.data/'commercial';self.folder.mkdir(parents=True,exist_ok=True)
        self.assets=self.folder/'assets';self.assets.mkdir(exist_ok=True);self.runtime=self.data/'runtime'/'commercial';self.runtime.mkdir(parents=True,exist_ok=True)
        self.path=self.folder/'settings.json';self.catalog=self.folder/'assets.json';self.lock=threading.RLock();self.config=CommercialConfig();self.revision=0;self.items=[];self.error=None;self.status={};self.sponsor_key=None;self.ad_key=None
        try:
            if self.path.exists():
                row=json.loads(self.path.read_text());self.config=CommercialConfig.model_validate(row['config']);self.revision=row['revision']
            if self.catalog.exists():self.items=json.loads(self.catalog.read_text())
        except (ValueError,KeyError,TypeError,OSError):self.error='Commercial settings could not be read; restore their backup.';self.config=CommercialConfig();self.items=[]
    def item(self,id):
        row=next((r for r in self.items if r['id']==id),None)
        if not row:raise KeyError('Asset not found')
        return row
    def file(self,id,poster=False):
        row=self.item(id);return self.assets/(id+('.png' if poster else row['extension']))
    def eligible(self,kind,now=None):
        setting=getattr(self.config,kind);now=now or datetime.now(timezone.utc)
        if self.error or not setting.active(now) or not setting.asset_id:return None
        try:
            row=self.item(setting.asset_id)
            return row if self.file(row['id']).is_file() and self.file(row['id'],True).is_file() else None
        except (KeyError,OSError):return None
    def public(self):
        with self.lock:return {'revision':self.revision,'config':self.config.model_dump(mode='json'),'assets':self.items,'error':self.error,'advertisement_ready':bool(self.eligible('advertisement')),'sponsor_ready':bool(self.eligible('sponsor')),'status':self.status}
    def save(self,body):
        with self.lock:
            if self.error:raise RuntimeError(self.error)
            if body.expected_revision!=self.revision:raise LibraryConflict('Commercial settings changed. Reload before saving.')
            for kind in ('advertisement','sponsor'):
                setting=getattr(body.config,kind)
                if setting.enabled and not setting.asset_id:raise ValueError('Choose an asset before enabling it')
                if setting.asset_id:
                    row=self.item(setting.asset_id)
                    if kind=='sponsor' and row['kind']!='image':raise ValueError('Sponsor artwork must be an image')
            from .playout import available
            backdrop=body.config.advertisement.background_asset_id
            if backdrop and self.item(backdrop)['kind']!='image':raise ValueError('Background artwork must be an image')
            if any(not available(s) for s in body.config.sponsor.scenes):raise ValueError('Unknown sponsor scene')
            save_json(self.path,{'revision':self.revision+1,'config':body.config.model_dump(mode='json')});self.config=body.config;self.revision+=1
            return self.public()
    def import_file(self,path,name):
        path=Path(path);ext=Path(name).suffix.lower();id=uuid.uuid4().hex
        if path.stat().st_size>MAX_UPLOAD:raise ValueError('Maximum upload is 100 MiB')
        with self.lock:
            if self.error:raise RuntimeError(self.error)
            if len(self.items)>=40:raise ValueError('The asset library holds 40 files')
            if ext in ('.png','.jpg','.jpeg','.webp'):
                with Image.open(path,formats=('PNG','JPEG','WEBP')) as im:
                    if im.width*im.height>40_000_000:raise ValueError('Image exceeds 40 megapixels')
                    im=ImageOps.exif_transpose(im).convert('RGBA');im.thumbnail((3840,2160),Image.Resampling.LANCZOS);w,h=im.size;im.save(self.assets/(id+'.png'))
                ext='.png';kind='image';duration=None;fps=None
            elif ext=='.mp4':
                from .media_probe import video_poster
                w,h,fps,duration,poster=video_poster(path)
                poster.save(self.assets/(id+'.png'))
                target=self.assets/(id+ext);path.replace(target);kind='video'
            else:raise ValueError('Upload PNG, JPEG, WebP or H.264 MP4')
            for asset in set((self.assets/(id+ext),self.assets/(id+'.png'))):
                with asset.open('r+b') as f:os.fsync(f.fileno())
            row={'id':id,'name':Path(name.replace('\\','/')).name[:100],'extension':ext,'kind':kind,'width':w,'height':h,'duration':duration,'fps':fps,'uploaded_at':time.time()}
            save_json(self.catalog,[*self.items,row]);self.items.append(row);return row
    def delete(self,id):
        with self.lock:
            if id in (self.config.advertisement.asset_id,self.config.sponsor.asset_id,self.config.advertisement.background_asset_id):raise ValueError('Unselect this asset from advertising, background and sponsor settings before deleting it')
            row=self.item(id);items=[r for r in self.items if r['id']!=id];save_json(self.catalog,items);self.items=items
            self.assets.joinpath(id+row['extension']).unlink(missing_ok=True);self.assets.joinpath(id+'.png').unlink(missing_ok=True)
            return self.public()
    def overlay_image(self):
        im=Image.new('RGBA',(3840,2160));d=ImageDraw.Draw(im)
        if self.config.advertisement.show_brand:brand(d)
        d.rectangle((192,1780,1100,1895),fill='#101c25');d.text((230,1804),'SPONSORED MESSAGE',font=font(56),fill=PAPER)
        return im
    def image(self,preview=True):
        row=self.eligible('advertisement');im=self.background() if row else Image.new('RGB',(3840,2160),'#0e1e29')
        if row:
            with Image.open(self.file(row['id'],True)) as source:
                pic=ImageOps.contain(source.convert('RGBA'),(3302,1858),Image.Resampling.LANCZOS)
                im.paste(pic,((3840-pic.width)//2,54+(1858-pic.height)//2),pic)
        else:
            d=ImageDraw.Draw(im);brand(d,1240,850,2)
        if row and preview:im.paste(self.overlay_image(),(0,0),self.overlay_image())
        return im
    def background(self):
        setting=self.config.advertisement
        im=Image.new('RGB',(3840,2160),setting.background_color)
        if setting.background_asset_id:
            try:
                with Image.open(self.file(setting.background_asset_id,True)) as source:
                    # Only the decorative background fills/crops; the ad keeps its aspect ratio.
                    pic=ImageOps.fit(source.convert('RGBA'),im.size,Image.Resampling.LANCZOS)
                    im.paste(pic,(0,0),pic)
            except (KeyError,OSError,ValueError):pass
        return im
    def cached(self,kind,image):
        key=hashlib.sha256(('copy-cleanup-'+kind+self.config.model_dump_json()+str(bool(self.eligible('advertisement')))+str(bool(self.eligible('sponsor')))).encode()).hexdigest()[:20]
        path=self.runtime/(kind+'-'+key+'.png')
        if not valid_image(path,(3840,2160)):
            temp=path.with_suffix('.tmp');image().save(temp,format='PNG',compress_level=1);temp.replace(path)
        for old in sorted(self.runtime.glob(kind+'-*.png'),key=lambda p:p.stat().st_mtime)[:-8]:old.unlink(missing_ok=True)
        return path
    def native(self,path):return '/workspace/runtime/commercial/'+path.name
    def media(self):
        with self.lock:
            row=self.eligible('advertisement')
            if row and row['kind']=='video':return {'path':'/workspace/data-web/commercial/assets/'+row['id']+'.mp4','video':True,'loop':self.config.advertisement.end_policy=='loop','background':self.native(self.cached('ad-background',self.background))}
            return self.native(self.cached('ad-base',lambda:self.image(False)))
    def overlay(self):
        return self.native(self.cached('ad-overlay',lambda:self.overlay_image() if self.eligible('advertisement') else Image.new('RGBA',(3840,2160))))
    def sponsor_image(self,scene):
        im=Image.new('RGBA',(3840,2160));row=self.eligible('sponsor');setting=self.config.sponsor
        if not row or scene not in setting.scenes or scene in ('advertisement','weather-alerts'):return im
        x=192 if setting.position=='left' else 3048;y=310;d=ImageDraw.Draw(im)
        d.rounded_rectangle((x,y,x+600,y+300),radius=12,fill='#101c25')
        d.text((x+24,y+15),setting.text,font=fit(d,setting.text,36,552),fill=PAPER)
        with Image.open(self.file(row['id'],True)) as source:
            pic=ImageOps.contain(source.convert('RGBA'),(540,205),Image.Resampling.LANCZOS)
            im.paste(pic,(x+(600-pic.width)//2,y+75+(205-pic.height)//2),pic)
        return im
    def decorate(self,bank,scene):
        with self.lock:
            if self.eligible('sponsor') and scene in self.config.sponsor.scenes and scene not in ('advertisement','weather-alerts'):
                from . import playout
                try:
                    path=self.cached('sponsor-'+scene,lambda:self.sponsor_image(scene));native=self.native(path)
                except (OSError,ValueError) as exc:
                    self.status={'error':'Sponsor artwork unavailable: '+str(exc)[:120]}
                    playout.command(f'CLEAR {bank}-18')
                    return
                playout.command(f'PLAY {bank}-18 "{native}"')
    def tick(self):
        from . import playout
        if not playout.STATUS.get('ready'):return
        # Take the engine lock first, matching the prepare path's lock order.
        with playout.LOCK,self.lock:
            scene=playout._camera
            key=(scene,playout._bank,self.revision,bool(self.eligible('sponsor')))
            if key!=self.sponsor_key:
                if self.eligible('sponsor') and scene in self.config.sponsor.scenes and scene not in ('advertisement','weather-alerts'):
                    self.decorate(playout._bank,scene)
                else:playout.command(f'CLEAR {playout._bank}-18')
                self.sponsor_key=key
            current=(self.revision,bool(self.eligible('advertisement')))
            if scene=='advertisement' and self.ad_key is not None and self.ad_key!=current:
                # Expiry or disable removes a video too, without changing program/music.
                desc=self.media();path=desc['path'] if isinstance(desc,dict) else desc
                if isinstance(desc,dict):playout.command(f'PLAY {playout._bank}-9 "{desc["background"]}"')
                else:playout.command(f'CLEAR {playout._bank}-9')
                if not isinstance(desc,dict):playout.command(f'MIXER {playout._bank}-10 CLEAR');playout.command(f'PLAY {playout._bank}-10 "{path}"')
                playout.command(f'PLAY {playout._bank}-20 "{self.overlay()}"')
            self.ad_key=current if scene=='advertisement' else None;self.status={'error':None,'sponsor_visible':bool(self.eligible('sponsor') and scene in self.config.sponsor.scenes)}
    async def watch(self):
        from . import playout
        if not playout.ENABLED:return
        while True:
            try:await asyncio.to_thread(self.tick)
            except Exception as exc:self.status={'error':str(exc)[:160]}
            await asyncio.sleep(.5)
