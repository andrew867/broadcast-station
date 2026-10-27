"""On-demand still scenes, archived source pictures and inexpensive operator observations."""
import asyncio
import json
import threading
import time
from datetime import datetime
from PIL import Image,ImageDraw,ImageOps
from pydantic import Field
from .models import StrictModel
from .picture_history import PictureHistory,enforce_budget
from .flight_features import Spotlight,altitude_color
from .community_cards import heading,MUTED
from .graphics import brand,font,fit,PAPER,ORANGE
from .daylight import TZ
from . import playout
from .sources import CAMERAS,QUADS

SCENES=('map-ocean','flight-spotlight','radar-history-east','radar-history-island','camera-timelapse')

class FeatureConfig(StrictModel):
    spotlight_hex:str|None=Field(default=None,pattern=r'^[a-zA-Z0-9]{1,16}$')
    timelapse_camera:str=Field(default='cam1',pattern=r'^[a-z0-9][a-z0-9_-]{0,47}$')

def local_time(at):return datetime.fromtimestamp(at,TZ).strftime('%b %d  %H:%M:%S %Z')

def saved_object(path, expected, fallback):
    """Diagnostic/history files must not stop startup when structurally damaged."""
    try:value=json.loads(path.read_text())
    except (OSError,ValueError):return fallback
    return value if isinstance(value,expected) else fallback

def saved_rows(path, limit):
    return [row for row in saved_object(path,list,[]) if isinstance(row,dict)][-limit:]

class FeatureScenes:
    def __init__(self,data,get_map,renderers):
        from .map_renderer import MapRenderer
        self.ocean=MapRenderer(data,get_map,scene='map-ocean',zoom=6,view_scale=.65)
        self.data=data;self.get_map=get_map;self.renderers=renderers;self.lock=threading.RLock()
        self.folder=data/'runtime'/'feature-scenes';self.folder.mkdir(parents=True,exist_ok=True)
        self.settings=data/'broadcast'/'features.json'
        try:self.config=FeatureConfig.model_validate_json(self.settings.read_text())
        except (OSError,ValueError):self.config=FeatureConfig()
        self.spotlight=Spotlight();self.spotlight.manual=self.config.spotlight_hex
        self.histories={};self.status={};self.events=[];self.previous={};self.last_collect=0
        self.event_path=data/'broadcast'/'source-events.json'
        self.events=saved_rows(self.event_path,100)

    def save(self,config):
        if config.timelapse_camera not in CAMERAS:raise ValueError('Choose a registered camera')
        with self.lock:
            self.settings.parent.mkdir(parents=True,exist_ok=True)
            temp=self.settings.with_suffix('.tmp');temp.write_text(config.model_dump_json(indent=2));temp.replace(self.settings)
            self.config=config;self.spotlight.manual=config.spotlight_hex

    def history(self,camera):
        if camera not in CAMERAS:raise ValueError('Unknown camera')
        with self.lock:
            if camera not in self.histories:self.histories[camera]=PictureHistory(self.data/'history'/'cameras'/camera,count=120,age=3600,budget=12*1024*1024)
            return self.histories[camera]

    def health(self):
        value=saved_object(self.data/'source-health.json',dict,{})
        if type(value.get('checked_at')) not in (int,float):value['checked_at']=0
        cameras=value.get('cameras',{})
        value['cameras']={k:v for k,v in cameras.items() if isinstance(v,dict)} if isinstance(cameras,dict) else {}
        return value

    def thumbnail(self,camera):
        if camera not in CAMERAS:raise ValueError('Unknown camera')
        return self.data/'runtime'/'confidence'/(camera+'.jpg')

    def collect(self):
        now=time.time();health=self.health();fresh=0<=now-health.get('checked_at',0)<5
        changed=False;due=now-self.last_collect>=30
        for camera in list(CAMERAS):
            if due:self.history(camera)
            row=health.get('cameras',{}).get(camera,{})
            state=(row.get('state','unavailable') if fresh else 'monitor unavailable',row.get('generation'))
            if camera in self.previous and state!=self.previous[camera]:
                self.events.append({'at':now,'camera':camera,'state':state[0],'generation':state[1]});changed=True
            self.previous[camera]=state
            if not due or not fresh or not row.get('ready'):continue
            path=self.thumbnail(camera)
            try:
                stamp=path.stat().st_mtime
                if 0<=now-stamp<=15:self.history(camera).add(path.read_bytes(),at=stamp)
            except (OSError,ValueError):pass
        if due:self.last_collect=now
        if changed:
            self.events=self.events[-100:];self.event_path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.event_path.with_suffix('.tmp');temp.write_text(json.dumps(self.events));temp.replace(self.event_path)
        # Retired camera IDs cannot accumulate permanent history directories.
        root=self.data/'history'/'cameras'
        retired=[]
        if due and root.exists():
            for folder in root.iterdir():
                if folder.is_dir() and not folder.is_symlink() and folder.name not in CAMERAS:
                    old=PictureHistory(folder,count=120,age=3600,budget=12*1024*1024)
                    old.prune();self.histories.pop(folder.name,None)
                    retired.append(old)
                    if not old.entries():
                        (folder/'index.json').unlink(missing_ok=True)
                        if not any(folder.iterdir()):folder.rmdir()
        if due:enforce_budget([*self.histories.values(),*retired],144*1024*1024)

    def public(self):
        return {'config':self.config.model_dump(),'scenes':list(SCENES),'status':self.status,
                'timelapse':self.history(self.config.timelapse_camera).public() if self.config.timelapse_camera in CAMERAS else {},
                'radar':{kind:self.renderers['radar-'+kind].history.public() for kind in ('east','island')},
                'aircraft':[{k:p.get(k) for k in ('hex','callsign','stale','lat','lon','age_s','altitude_ft')} for p in self.get_map()['aircraft']]}

    def confidence(self):
        now=time.time();health=self.health();sources=[]
        for camera,row in list(CAMERAS.items()):
            h=health.get('cameras',{}).get(camera,{});path=self.thumbnail(camera)
            stamp=path.stat().st_mtime if path.exists() else 0
            recent=0<=now-stamp<15 and 0<=now-health.get('checked_at',0)<5 and h.get('ready',False)
            sources.append({'id':camera,'name':row['name'],'at':stamp or None,'fresh':bool(recent),'state':h.get('state','unavailable'),
                            'generation':h.get('generation'),'url':f'/api/confidence/camera/{camera}' if stamp else None,
                            'native':playout.STATUS.get('cameras',{}).get(camera,{})})
        meter=playout.STATUS.get('audio',{})
        meter={**meter,'available':bool(meter.get('available') and 0<=now-meter.get('at',0)<3)}
        watchdog=saved_object(self.data/'runtime'/'watchdog.json',dict,{})
        recoveries=saved_rows(self.data/'broadcast'/'watchdog-history.json',40)
        if not recoveries:
            history=watchdog.get('history',[])
            recoveries=[row for row in history if isinstance(row,dict)][-40:] if isinstance(history,list) else []
        output=dict(playout.STATUS.get('output') or {})
        if not 0<=now-playout.STATUS.get('checked_at',0)<5:output.update(moving=False,measured_fps=None)
        return {'at':now,'sources':sources,'audio':meter,'program':playout.STATUS.get('program'),
                'preview':playout.STATUS.get('preview'),'output':output,
                'recoveries':recoveries,'watchdog_at':watchdog.get('checked_at'),'events':self.events[-40:],
                'limits':'Source snapshots are independent decoded inputs, not a pixel-exact program or prepared-bank monitor. Audio is sampled before encoding.'}

    def spotlight_image(self):
        data=self.get_map();plane=self.spotlight.select(data['aircraft'],data['healthy'])
        im,d=heading('FLIGHT SPOTLIGHT','AIRCRAFT IN RECEIVER RANGE')
        if plane is None:
            d.text((240,820),'NO AIRCRAFT AVAILABLE',font=font(100),fill=PAPER)
            return im
        renderer=self.renderers['map-island']
        with renderer.lock:
            if renderer.base is None:renderer.basemap()
            map_im,_=renderer.draw({**data,'aircraft':[plane],'theme':{**data['theme'],'show_info':False}})
        # Keep an actual geographic map and its attribution; never stretch its aspect ratio.
        map_im=map_im.crop((0,0,3840,1920)).resize((2320,1160),Image.Resampling.LANCZOS)
        im.paste(map_im,(192,625));d=ImageDraw.Draw(im)
        x=2610;d.text((x,635),plane['callsign'],font=fit(d,plane['callsign'],145,1038),fill=PAPER)
        d.text((x,825),'ALTITUDE / GEOMETRIC',font=font(42),fill=MUTED)
        d.text((x,892),f"{plane['altitude_ft']:,.0f} ft",font=font(112),fill=altitude_color(plane))
        d.text((x,1070),'GROUND SPEED / TRACK',font=font(42),fill=MUTED)
        speed=plane.get('speed_kt');label=(f'{speed:.0f} kt' if speed is not None else 'Unknown')+f" / {plane['track']:.0f}°"
        d.text((x,1135),label,font=fit(d,label,86,1038),fill=PAPER)
        metadata=' / '.join(filter(None,[plane.get('registration'),plane.get('aircraft_type'),'HELICOPTER' if plane.get('category')=='A7' else '']))
        if metadata:d.text((x,1335),metadata,font=fit(d,metadata,42,1038),fill='#ffb578')
        if plane.get('metadata_source'):d.text((x,1410),plane['metadata_source'],font=font(28,False),fill=MUTED)
        d.text((x,1495),f"Position {plane['age_s']:.0f}s ago",font=font(42,False),fill=MUTED)
        px,py=renderer.point(plane['lat'],plane['lon'])
        if not renderer.contains(px,py):d.text((x,1685),'OUTSIDE MAP VIEW',font=font(48),fill=ORANGE)
        d.text((192,1830),'2-MINUTE TRAIL',font=font(40),fill=MUTED)
        return im

    def replay_image(self,scene,index):
        radar=scene.startswith('radar-history-')
        camera=self.config.timelapse_camera
        history=self.renderers['radar-'+scene.rsplit('-',1)[1]].history if radar else self.history(camera) if camera in CAMERAS else None
        rows=[];source=row=None
        if history:
            with history.lock:
                source,row=history.frame(index)
                rows=history.entries()
        title=('EAST RADAR HISTORY' if scene.endswith('east') else 'ISLAND RADAR HISTORY') if radar else 'CAMERA TIMELAPSE'
        subtitle='REPLAY' if radar else (CAMERAS.get(camera,{}).get('name','Camera unavailable').upper()+' / TIMELAPSE')
        im,d=heading(title,subtitle)
        if source is None:
            d.text((240,850),'REPLAY UNAVAILABLE',font=font(130),fill=PAPER)
            return im
        picture=ImageOps.contain(source,(2304,1296),Image.Resampling.LANCZOS);im.paste(picture,(192,600))
        d=ImageDraw.Draw(im);x=2610
        d.text((x,650),'REPLAY',font=font(108),fill=ORANGE)
        d.text((x,825),'FIRST RECEIVED' if radar else 'SNAPSHOT SAVED',font=font(44),fill=MUTED)
        d.text((x,905),local_time(row['at']),font=fit(d,local_time(row['at']),65,1038),fill=PAPER)
        selected=next(i for i,r in enumerate(rows) if r['file']==row['file'])
        d.text((x,1120),'RECEIVED RANGE' if radar else 'CAPTURE RANGE',font=font(44),fill=MUTED)
        d.text((x,1200),local_time(rows[0]['at']),font=fit(d,local_time(rows[0]['at']),52,1038),fill=PAPER)
        d.text((x,1280),local_time(rows[-1]['at']),font=fit(d,local_time(rows[-1]['at']),52,1038),fill=PAPER)
        gap=row['at']-rows[selected-1]['at'] if selected else 0
        if gap>(180 if radar else 75):d.text((x,1370),f'GAP BEFORE: {gap/60:.1f} MIN',font=font(52),fill='#ffb578')
        age=time.time()-rows[-1]['at']
        note='SOURCE DELAYED' if age>(600 if radar else 90) else ''
        if note:d.text((x,1460),note,font=font(54),fill=MUTED)
        credit='RADAR COURTESY SHEERR WEATHER' if radar else CAMERAS.get(camera,{}).get('attribution_text','') if CAMERAS.get(camera,{}).get('attribution_enabled') else ''
        d.text((x,1625),credit,font=fit(d,credit,40,1038),fill=MUTED)
        return im

    def path(self,scene,index=0):
        if scene not in SCENES:raise ValueError('Unknown feature scene')
        with self.lock:
            if scene=='map-ocean':
                if self.ocean.base is None or time.time()-self.ocean.built_at>7*86400:self.ocean.basemap()
                im,_=self.ocean.draw(self.get_map())
                d=ImageDraw.Draw(im);d.rectangle((172,92,872,258),fill="#101c25");brand(d)
            else:im=self.spotlight_image() if scene=='flight-spotlight' else self.replay_image(scene,index)
            path=self.folder/f'{scene}-{time.time_ns()}.png';temp=path.with_suffix('.tmp')
            im.resize((1920,1080),Image.Resampling.LANCZOS).save(temp,format='PNG',compress_level=1);temp.replace(path)
            preview=self.folder/(scene+'.jpg');temp=preview.with_suffix('.tmp');im.resize((960,540)).convert('RGB').save(temp,format='JPEG',quality=85);temp.replace(preview)
            for old in sorted(self.folder.glob(scene+'-*.png'))[:-4]:old.unlink(missing_ok=True)
            self.status[scene]={'updated_at':time.time(),'error':None}
            return path

    def media(self,scene):return '/workspace/runtime/feature-scenes/'+self.path(scene).name

    async def watch(self):
        active=None;index=0
        while True:
            try:
                await asyncio.to_thread(self.collect)
                scene=playout._camera;bank=playout._bank
                if playout.STATUS.get('ready') and scene in SCENES:
                    if active!=(scene,bank):active=(scene,bank);index=0
                    path=await asyncio.to_thread(self.path,scene,index)
                    with playout.LOCK:
                        if (playout._camera,playout._bank)==active:playout.command(f'PLAY {bank}-10 "/workspace/runtime/feature-scenes/{path.name}"')
                    index+=1
                else:active=None
            except Exception as exc:self.status['error']=str(exc)[:180]
            await asyncio.sleep(2)
