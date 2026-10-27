from .station_config import CONFIG,clock_label
from .branding import BRAND
"""Rasterize ticker text once; CasparCG moves it at the channel frame rate."""
import asyncio,hashlib,json,time,math
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw
from .graphics import font,fit,PAPER,INK,ORANGE,TICKER_TOP,TICKER_HEIGHT,TICKER_TEXT_HEIGHT
from . import playout
from .alert_graphics import emergency_rows,emergency_image
from .outages import banner_image
from .image_cache import valid_image
STRIP_LAYERS=tuple(range(22,40))
BADGE_LAYER=40
ITEM_GAP=96
Y=TICKER_TOP/2160;TEXT_H=TICKER_TEXT_HEIGHT/2160;BAR_H=TICKER_HEIGHT/2160

class NativeTicker:
    def __init__(self,data,broadcast,alerts=None,outages=None,presentation=None):
        self.folder=data/'ticker';self.folder.mkdir(parents=True,exist_ok=True)
        self.broadcast=broadcast;self.started=False;self.next_at=0;self.index=0;self.layer=22;self.badge_key=None;self.active={};self.status={}
        self.settings=None;self.on_air={};self.last_strip=None;self.graphics_epoch=None
        self.presentation_folder=data/'runtime'/'alert-bars';self.presentation_folder.mkdir(parents=True,exist_ok=True)
        self.presentation=presentation;self.outages=outages;self.outage_active=False
        self.presentation_mode=None
        self.alerts=alerts;self.emergency_key=None;self.emergency_started=0;self.emergency_init=False;self.emergency_rows=[];self.emergency_set=None
    def emergency(self,now):
        if self.presentation is not None:return self.present()
        data=self.alerts() if self.alerts else {};items=data.get('immediate',[])
        outage=self.outages() if not items and self.outages else None
        if outage:
            key='outage-'+hashlib.sha256(json.dumps(outage,sort_keys=True).encode()).hexdigest()[:24]
            with playout.LOCK:
                if key!=self.emergency_key:
                    path=self.save_image(banner_image(outage),key)
                    playout.command(f'MIXER 1-41 FILL 0 {Y} 1 {BAR_H}')
                    playout.command(f'PLAY 1-41 "{path}"')
                    for layer in range(21,41):playout.command(f'CLEAR 1-{layer}')
                    self.emergency_key=key;self.emergency_init=True;self.started=False;self.badge_key=None;self.on_air={};self.active={}
                self.outage_active=True;self.status={'renderer':'native','emergency':False,'outage_banner':True}
            return True
        if self.outage_active:
            self.emergency_set=None;self.outage_active=False
        key=json.dumps(items,sort_keys=True)
        if key!=self.emergency_set:
            self.emergency_rows=emergency_rows(items);self.emergency_set=key;self.emergency_started=now
        with playout.LOCK:
            if not self.emergency_rows:
                if self.emergency_key or not self.emergency_init:
                    playout.command('CLEAR 1-41');playout.command('MIXER 1-41 CLEAR')
                    self.emergency_init=True;self.emergency_key=None;self.started=False;self.badge_key=None
                self.status['emergency']=False
                return False
            row=self.emergency_rows[int((now-self.emergency_started)//22)%len(self.emergency_rows)]
            picture_key=hashlib.sha256(json.dumps([row,data.get('fresh'),1],sort_keys=True).encode()).hexdigest()[:24]
            if picture_key!=self.emergency_key:
                path=self.save_image(emergency_image(row,data.get('fresh',False)),'emergency-'+picture_key)
                playout.command('MIXER 1-41 FILL 0 0.705555556 1 0.294444444')
                playout.command(f'PLAY 1-41 "{path}"')
                if self.emergency_key is None:
                    for layer in range(21,41):playout.command(f'CLEAR 1-{layer}')
                self.emergency_key=picture_key;self.emergency_init=True
                self.started=False;self.badge_key=None;self.on_air={};self.active={}
            self.status={'renderer':'native','emergency':True,'identifier':row['alert']['identifier'],'page':row['part'],'pages':row['parts']}
            return True
    def present(self):
        from .alert_graphics import summary_image
        if self.presentation.audio:self.presentation.audio.recover()
        frame=self.presentation.frame()
        if frame is None:
            with playout.LOCK:
                if self.emergency_key or not self.emergency_init:
                    playout.command('CLEAR 1-41');playout.command('MIXER 1-41 CLEAR')
                    self.emergency_key=None;self.emergency_init=True;self.presentation_mode=None;self.started=False;self.badge_key=None
            self.status={'renderer':'native','emergency':False,'presentation':self.presentation.public()}
            return False
        full=frame['mode']=='full'
        changed_mode=self.presentation_mode!=frame['mode']
        key=hashlib.sha256(json.dumps([frame,'compact-summary-v2'],sort_keys=True).encode()).hexdigest()[:24]
        if key!=self.emergency_key:
            image=emergency_image(frame['row'],frame['fresh']) if frame['mode']=='full' else summary_image(frame)
            # Only four recent countdown images are retained, on the memory-backed runtime.
            path=self.presentation_folder/('active-'+key+'.png');tmp=path.with_suffix('.tmp');image.save(tmp,format='PNG',compress_level=1);tmp.replace(path)
            media='/workspace/runtime/alert-bars/'+path.name
            with playout.LOCK:
                h=image.height/2160;playout.command(f'MIXER 1-41 FILL 0 {1-h} 1 {h}')
                playout.command(f'PLAY 1-41 "{media}"')
                if full and changed_mode:
                    for layer in range(21,41):playout.command(f'CLEAR 1-{layer}')
                self.emergency_key=key;self.emergency_init=True
                if changed_mode:
                    self.started=False;self.badge_key=None;self.on_air={};self.active={};self.last_strip=None
                self.presentation_mode=frame['mode']
        for old in sorted(self.presentation_folder.glob('*.png'),key=lambda p:p.stat().st_mtime)[:-4]:old.unlink(missing_ok=True)
        self.status={'renderer':'native','emergency':frame['kind']=='emergency','outage_banner':frame['kind']=='utility','presentation':self.presentation.public()}
        return full

    def save_image(self,image,name):
        path=self.folder/(name+'.png')
        if not valid_image(path,image.size):
            tmp=path.with_suffix('.tmp');image.save(tmp,format='PNG',compress_level=1);tmp.replace(path)
        return '/workspace/data-web/ticker/'+path.name
    def badge(self,category):
        clock=datetime.now(ZoneInfo(CONFIG.location.timezone)).strftime('%H:%M')
        key='station-v2'+BRAND.fingerprint()+clock+category+clock_label()
        if key==self.badge_key:return
        image=Image.new('RGBA',(3840,TICKER_HEIGHT));d=ImageDraw.Draw(image)
        d.rectangle((0,0,560,TICKER_HEIGHT),fill='#101c25');d.rectangle((3320,0,3840,TICKER_TEXT_HEIGHT),fill='#e4dfd4')
        d.rectangle((0,TICKER_TEXT_HEIGHT,3840,TICKER_HEIGHT),fill='#101c25')
        d.text((192,30),BRAND.station_short,font=fit(d,BRAND.station_short,68,340,minimum=12),fill=PAPER);d.text((192,112),category,font=font(32,False),fill=ORANGE)
        for text,size,y in [(clock,82,20),(clock_label(),30,116)]:
            f=fit(d,text,size,300,size==82,18);d.text((3484-d.textlength(text,font=f)/2,y),text,font=f,fill='#101c25')
        path=self.save_image(image,'badge-'+hashlib.sha256(key.encode()).hexdigest()[:16])
        playout.command(f'MIXER 1-{BADGE_LAYER} FILL 0 {Y} 1 {BAR_H}')
        playout.command(f'PLAY 1-{BADGE_LAYER} "{path}"');self.badge_key=key
    def invalidate_native(self):
        # Native layers disappear on engine replacement even if this controller
        # survives. Keep the alert schedule, but recreate its picture and crawl.
        self.started=False;self.badge_key=None;self.on_air={};self.active={}
        self.last_strip=None;self.settings=None;self.next_at=0
        self.emergency_key=None;self.emergency_init=False;self.presentation_mode=None

    def tick(self):
        if not playout.STATUS.get('ready'):
            self.invalidate_native()
            if self.presentation and self.presentation.audio:
                with self.presentation.lock:
                    self.presentation.audio.engine_lost();self.presentation.audio_started=False
            return
        epoch=playout.STATUS.get('graphics_epoch',0)
        if epoch!=self.graphics_epoch:
            self.invalidate_native();self.graphics_epoch=epoch
        if self.emergency(time.monotonic()):return
        data=self.broadcast.public();state=data['state'];now=time.monotonic()
        items=data['headlines'] or [{'title':state['ticker_note'],'source':BRAND.station_short}]
        eligible={(item['source'],item['title']) for item in items}
        settings=(state['ticker_speed'],state['ticker_note'],tuple(state['news_sources']),state.get('news_mix','standard'))
        with playout.LOCK:
            if not state['show_ticker'] or state['scene']=='clean' or (getattr(self,'suppress',None) and self.suppress()):
                if self.started:
                    for layer in range(21,BADGE_LAYER+1):playout.command(f'CLEAR 1-{layer}')
                self.started=False;self.badge_key=None;self.on_air={};return
            # A deselected/expired headline must leave air immediately. A speed
            # change also starts a fresh strip, without touching the scene/music.
            if settings!=self.settings or any(entry[0] not in eligible for entry in self.on_air.values()):
                for layer in STRIP_LAYERS:playout.command(f'CLEAR 1-{layer}')
                self.next_at=0;self.index=0;self.on_air={};self.active={};self.last_strip=None;self.settings=settings
            if not self.started:
                for layer in range(21,BADGE_LAYER+1):playout.command(f'CLEAR 1-{layer}');playout.command(f'MIXER 1-{layer} CLEAR')
                image=Image.new('RGB',(3840,TICKER_HEIGHT),'#101c25');draw=ImageDraw.Draw(image)
                draw.rectangle((0,0,3840,TICKER_TEXT_HEIGHT),fill=PAPER);draw.rectangle((0,0,3840,5),fill=ORANGE)
                path=self.save_image(image,'bar-reference-v3');playout.command(f'MIXER 1-21 FILL 0 {Y} 1 {BAR_H}');playout.command(f'PLAY 1-21 "{path}"')
                self.started=True;self.next_at=0;self.active={};self.on_air={};self.last_strip=None
            self.badge('HEADLINES' if data['headlines'] else BRAND.station_name)
            # Mixer animation advances in program frames. Wall-clock expiry
            # made headlines collide whenever output fell below 60 fps.
            positions={}
            for old_layer in list(self.on_air):
                reply=playout.command(f'MIXER 1-{old_layer} FILL',lines=2)
                values=reply.splitlines()[1].split()
                if len(values)!=4:raise RuntimeError('Ticker position unavailable')
                x,y,w,h=map(float,values);positions[old_layer]=(x,w)
                if x+w<=0:
                    playout.command(f'CLEAR 1-{old_layer}');self.on_air.pop(old_layer);self.active.pop(old_layer,None)
            start=1.0
            if self.last_strip in self.on_air:
                x,w=positions[self.last_strip]
                start=x+w+ITEM_GAP/3840
                if start>1:return
                start=max(0,start)

            layer=next((layer for layer in STRIP_LAYERS if layer not in self.on_air),None)
            if layer is None:return
            item=items[self.index%len(items)];self.index+=1
            title=item['title'];source=item.get('display_source',item['source']).upper();f=font(84,False);sf=font(56)
            dummy=ImageDraw.Draw(Image.new('RGB',(1,1)));sw=round(dummy.textlength(source,font=sf))+55
            width=max(64,min(16000,math.ceil(sw+dummy.textlength(title,font=f)+24)))
            image=Image.new('RGBA',(width,TICKER_TEXT_HEIGHT));d=ImageDraw.Draw(image)
            d.text((15,60),source,font=sf,fill='#a44120');d.text((sw,35),title,font=f,fill='#101c25')
            path=self.save_image(image,hashlib.sha256((source+title+'84-natural-160-v3').encode()).hexdigest()[:24])
            speed=state['ticker_speed']
            duration=max(1,round((start*3840+width)/speed*playout.PROGRAM_FPS))
            playout.command(f'CLEAR 1-{layer}')
            playout.command(f'MIXER 1-{layer} FILL {start} {Y} {width/3840} {TEXT_H}')
            playout.command(f'PLAY 1-{layer} "{path}"')
            playout.command(f'MIXER 1-{layer} FILL {-width/3840} {Y} {width/3840} {TEXT_H} {duration} LINEAR')
            self.next_at=now+(width+ITEM_GAP)/speed;self.active[layer]=path;self.last_strip=layer
            self.on_air[layer]=((item['source'],item['title']),now+duration/playout.PROGRAM_FPS)
            self.status.update({'renderer':'native','spacing_clock':'mixer_position','font_px':84,'speed':speed,'headline':title,'item_width_px':width,'gap_px':ITEM_GAP})
            keep={p.rsplit('/',1)[-1] for p in self.active.values()}
            # Bound cache without removing the images currently used by CasparCG.
            for old in sorted(self.folder.glob('*.png'),key=lambda p:p.stat().st_mtime)[:-24]:
                if old.name not in keep:old.unlink(missing_ok=True)
    async def watch(self):
        if not playout.ENABLED:return
        while True:
            try:await asyncio.to_thread(self.tick)
            except Exception as exc:self.status['error']=str(exc)[:200]
            await asyncio.sleep(.25)
