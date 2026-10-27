from .station_config import CONFIG
"""Native map frames: fresh ADS-B at 1 Hz, cached basemap, no on-air browser.

Only tiles intersecting the displayed viewport are requested. Tile cache lasts
at least seven days. Program video, ticker, and music remain at 60 Hz.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import math
import os
import time
import threading
from PIL import Image,ImageDraw,ImageOps
import httpx
from .graphics import font,fit,SAFE_LEFT,SAFE_RIGHT,TICKER_TOP
from . import playout
from .flight_features import altitude_color,BANDS
from .map_theme import LATITUDE,LONGITUDE

# Approximate static offshore field references, not current FPSO positions.
# Hebron operator Benefits Plan (2011), figure 1.3.1-1; Hibernia government
# status report (1997); Titanic NOAA expedition instructions (2004).
LANDMARKS=(
    ('HIBERNIA',46+45/60+2.1/3600,-(48+46/60+59.2/3600),'PLATFORM'),
    ('HEBRON',46+32.64/60,-(48+29.88/60),'FIELD'),
    ('TERRA NOVA',46+28.53/60,-(48+28.86/60),'FIELD'),
    ('WHITE ROSE',46+47.33/60,-(48+.99/60),'FIELD'),
    ('TITANIC',41+43/60+35/3600,-(49+56/60+54/3600),'WRECK SITE'),
)


def draw_aircraft_symbol(d,x,y,angle,category,fill,outline,width=2):
    """Distinct overhead rotorcraft silhouette, stable at TV viewing size."""
    c=math.cos(angle);s=math.sin(angle)
    def points(shape):return [(x+a*c-b*s,y+a*s+b*c) for a,b in shape]
    def line(shape,thickness):
        q=points(shape);d.line(q,fill=outline,width=thickness+width*2);d.line(q,fill=fill,width=thickness)
    if category=='A7':
        # Tail boom, tail rotor and parallel skids, no airplane wing polygon.
        line([(0,4),(0,30)],5)
        line([(-8,25),(8,25)],4)
        for side in (-1,1):line([(side*13,-12),(side*13,13)],3)
        body=points([(0,-22),(7,-18),(9,-9),(8,4),(4,11),(-4,11),(-8,4),(-9,-9),(-7,-18)])
        d.polygon(body,fill=fill);d.line(body+[body[0]],fill=outline,width=width)
        # Crossed main rotor is wider than the fuselage and reads as a rotor.
        line([(-27,-24),(27,16)],4)
        line([(-27,16),(27,-24)],4)
    else:
        q=points([(0,-29),(5,-11),(25,6),(25,12),(5,4),(4,20),(13,27),(13,31),(0,26),(-13,31),(-13,27),(-4,20),(-5,4),(-25,12),(-25,6),(-5,-11)])
        d.polygon(q,fill=fill);d.line(q+[q[0]],fill=outline,width=width)

def close_reports(a,b):
    """Limit grouping to 500 metres as well as screen overlap at wide zooms."""
    dy=math.radians(a['lat']-b['lat'])
    dx=math.radians(a['lon']-b['lon'])*math.cos(math.radians((a['lat']+b['lat'])/2))
    return math.hypot(dx,dy)*6371<=.5

def night_basemap(image):
    # Matches the browser's sRGB SVG filter; applied only to cached base tiles.
    return ImageOps.colorize(ImageOps.invert(ImageOps.grayscale(image)),
                            black='#14283a',white='#d1e2ec').convert('RGBA')

def world(lat,lon,zoom=8):
    lat=max(-85,min(85,lat));size=256*2**zoom
    return (lon+180)/360*size,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*size


def label_box(x,y,width,occupied,height=60,gap=8):
    """Place labels near their aircraft without hiding other labels or graphics."""
    for dy in (-12,-84,60,-156,132,-228,204):
        for dx in (34,-width-34,110,-width-110):
            lx=min(max(SAFE_LEFT,x+dx),SAFE_RIGHT-width);ly=max(290,min(1770,y+dy))
            candidate=(lx,ly,lx+width,ly+height)
            if all(candidate[2]+gap<a or candidate[0]>c+gap or candidate[3]+gap<b or candidate[1]>d+gap for a,b,c,d in occupied):
                return candidate
    return None  # Aircraft symbol remains visible when the nearby labels are full.


# Bounded label-consolidation areas, not navigational harbour boundaries.
HARBOUR_LABEL_AREAS=(
    (47.55,47.58,-52.725,-52.68),
    (48.95,48.98,-58.04,-57.92),
    (50.63,50.66,-57.31,-57.25),
    (50.695,50.715,-57.37,-57.33),
)


def vessel_groups(vessels,point,contains,consolidate_harbours=False):
    """Keep moving reports individual; group overlapping slow/unknown reports.

    Pixel proximity is a visual grouping, not a claim about harbour boundaries.
    Anchor each group at an actual report, never move it to a made-up position.
    """
    groups=[];harbours={}
    ordered=sorted(vessels,key=lambda v:(bool(v.get('stale')),not ((v.get('sog') or 0)>.5),v['age_s'],v['mmsi']))
    for v in ordered:
        x,y=point(v['lat'],v['lon'])
        if not contains(x,y):continue
        harbour=next((i for i,(south,north,west,east) in enumerate(HARBOUR_LABEL_AREAS)
                      if south<=v['lat']<=north and west<=v['lon']<=east),None) if consolidate_harbours else None
        if harbour is not None:
            if harbour not in harbours:
                harbours[harbour]={'x':x,'y':y,'moving':False,'stale':True,'members':[],'harbour':harbour}
                groups.append(harbours[harbour])
            group=harbours[harbour];group['members'].append(v)
            group['stale']=group['stale'] and bool(v.get('stale'))
            continue
        moving=(v.get('sog') or 0)>.5
        group=next((g for g in groups if 'harbour' not in g and not moving and not g['moving'] and
                    g['stale']==bool(v.get('stale')) and close_reports(g['members'][0],v) and (g['x']-x)**2+(g['y']-y)**2<=64**2),None)
        if group:group['members'].append(v)
        else:groups.append({'x':x,'y':y,'moving':moving,'stale':bool(v.get('stale')),'members':[v]})
    return groups

class MapRenderer:
    def __init__(self,data,get_data,scene='map',channel=8,center=(LATITUDE,LONGITUDE),zoom=8,view_scale=1):
        self.scene=scene;self.channel=channel;self.zoom=zoom;self.lock=threading.RLock()
        self.center=center;self.view_scale=view_scale;self.source_width=round(1920/view_scale);self.source_height=round(1080/view_scale)
        self.scale_x=3840/self.source_width;self.scale_y=2160/self.source_height
        self.folder=data/'map';self.folder.mkdir(parents=True,exist_ok=True)
        self.frames=data/'runtime'/scene;self.frames.mkdir(parents=True,exist_ok=True)
        self.get_data=get_data;self.base=None;self.night_base=None;self.seq=0;self.built_at=0
        self.cx,self.cy=world(*center,zoom);self.left=self.cx-self.source_width/2;self.top=self.cy-self.source_height/2
        self.status={'ready':False,'error':None}
        if scene in ('map','map-island','map-ocean'):
            self.protect_aircraft=True;self.label_size=48;self.label_height=72;self.label_gap=16;self.label_limit=20
    def tile(self,xy):
        x,y=xy;path=self.folder/f'tile-{self.zoom}-{x}-{y}.png'
        try:
            if not path.exists() or time.time()-path.stat().st_mtime>7*86400:
                template=os.environ.get('SKYCAM_TILE_URL','https://tile.openstreetmap.org/{z}/{x}/{y}.png')
                response=httpx.get(template.format(z=self.zoom,x=x,y=y),timeout=8,headers={'User-Agent':'StJohnsSkyCam/1.0 (Andrew867 broadcast map)'})
                response.raise_for_status();image=Image.open(io.BytesIO(response.content),formats=('PNG','JPEG'));image.load()
                tmp=path.with_suffix('.tmp');image.save(tmp,format='PNG');tmp.replace(path)
            with Image.open(path) as image:return x,y,image.convert('RGB')
        except Exception:
            if path.exists():
                with Image.open(path) as image:return x,y,image.convert('RGB')
            return x,y,None
    def basemap(self):
        base=Image.new('RGB',(self.source_width,self.source_height),'#b5d6e7')
        coords=[(x,y) for x in range(math.floor(self.left/256),math.floor((self.left+self.source_width-1)/256)+1)
                       for y in range(math.floor(self.top/256),math.floor((self.top+self.source_height-1)/256)+1)]
        missing=0
        with ThreadPoolExecutor(max_workers=3) as pool:
            for x,y,tile in pool.map(self.tile,coords):
                if tile is None:missing+=1;continue
                base.paste(tile,(round(x*256-self.left),round(y*256-self.top)))
        self.status['missing_tiles']=missing;self.base=base.resize((3840,2160),Image.Resampling.LANCZOS).convert('RGBA');self.built_at=time.time()
        self.night_base=night_basemap(self.base)
    def point(self,lat,lon):
        x,y=world(lat,lon,self.zoom);return round((x-self.left)*self.scale_x),round((y-self.top)*self.scale_y)
    def contains(self,x,y):return 0<x<3840 and 0<y<1920
    def heading(self,p):return math.radians(p.get('track') or 0)
    def occupied(self):return [(172,92,880,280),(2700,108,3648,320),(3000,1792,3648,1868)]
    def receiver_guides(self,draw,night):
        x,y=self.point(*self.center);color='#6b879a' if night else '#6d8e9a'
        lat,lon=map(math.radians,self.center)
        for distance in ([100,200] if self.scene=='map' else [250,500]):
            arc=distance/6371;points=[]
            for bearing in range(361):
                b=math.radians(bearing);a=math.asin(math.sin(lat)*math.cos(arc)+math.cos(lat)*math.sin(arc)*math.cos(b))
                o=lon+math.atan2(math.sin(b)*math.sin(arc)*math.cos(lat),math.cos(arc)-math.sin(lat)*math.sin(a))
                points.append(self.point(math.degrees(a),math.degrees(o)))
            for i in range(0,358,6):draw.line(points[i:i+3],fill=color,width=2)
            px,py=points[135]
            if self.contains(px,py):draw.text((px+10,py),f'{distance} km',font=font(30),fill=color)
        draw.ellipse((x-10,y-10,x+10,y+10),fill='#ff995e',outline='#101c25',width=3)
        box=(x-180,y+35,x+180,y+97)
        draw.rounded_rectangle(box,radius=8,fill='#172a37',outline='#7893a5',width=2)
        draw.text((x-155,y+43),CONFIG.location.name.upper()+' / RX',font=font(36),fill='#f4f0e7')
        return [(x-24,y-24,x+24,y+24),box]
    def landmarks(self,draw,night,occupied=None):
        boxes=list(occupied or []);initial=len(boxes);visible=[];labelled=[];positions=[]
        for name,lat,lon,kind in LANDMARKS:
            x,y=self.point(lat,lon)
            if not self.contains(x,y):continue
            positions.append((name,kind,x,y));boxes.append((x-18,y-18,x+18,y+18))
        for name,kind,x,y in positions:
            visible.append(name)
            text=name+' / '+kind;w=draw.textlength(text,font=font(32))+28
            box=label_box(x,y,w,boxes,56,12)
            draw.rectangle((x-10,y-10,x+10,y+10),fill='#f4ca71',outline='#152635',width=3)
            if box:
                draw.line(((x,y),(max(box[0],min(box[2],x)),max(box[1],min(box[3],y)))),fill='#997c3e',width=3)
                draw.rounded_rectangle(box,radius=6,fill='#152635',outline='#f4ca71',width=2)
                draw.text((box[0]+12,box[1]+6),text,font=font(32),fill='#f4ca71')
                boxes.append(box);labelled.append(name)
        self.status['landmarks']={'in_view':visible,'labelled':labelled,'label_boxes':[list(b) for b in boxes[initial+len(positions):]],'note':'Static approximate field references, not live FPSO locations'}
        return boxes[initial:]

    def draw(self,data):
        night=data.get('theme',{}).get('effective')=='night'
        if night and self.night_base is None:self.night_base=night_basemap(self.base)
        image=(self.night_base if night else self.base).copy();d=ImageDraw.Draw(image);visible=0;fresh_visible=0;placed=[]
        label_bg='#152635' if night else '#fffff5';label_fg='#edf3f8' if night else '#17212c'
        label_bg=getattr(self,'label_background',label_bg);label_fg=getattr(self,'label_foreground',label_fg)
        occupied=self.occupied()
        boats=data.get('ais',{}) if self.scene in ('map','map-island','map-ocean') else {}
        boats=boats if boats.get('config',{}).get('show_on_maps') else {}
        if getattr(self,'protect_aircraft',False):
            for plane in data['aircraft']:
                px,py=self.point(plane['lat'],plane['lon'])
                if self.contains(px,py):occupied.append((px-28,py-32,px+28,py+32))
        if self.scene in ('map','map-island','map-ocean'):
            occupied+=self.receiver_guides(d,night)
            occupied+=self.landmarks(d,night,occupied)
            occupied.append((172,1690,2670,1858))
        if boats:
            occupied.append((2680,324,3668,560))
            for v in boats.get('vessels',[]):
                vx,vy=self.point(v['lat'],v['lon'])
                if self.contains(vx,vy):occupied.append((vx-25,vy-25,vx+25,vy+25))
        # Reserve boat label space before aircraft labels. Underway boats must
        # not lose every label to alphabetical harbour entries or plane labels.
        if boats:self.draw_vessels(d,boats,occupied,night)
        if data['aircraft']:
            for p in sorted(data['aircraft'],key=lambda p:(bool(p.get('stale')),p['callsign'])):
                x,y=self.point(p['lat'],p['lon'])
                if not self.contains(x,y):continue
                visible+=1
                fresh_visible+=not p.get('stale',False)
                for segment in p.get('trail_segments',[p.get('trail',[])]):
                    previous=None
                    for q in segment:
                        point=self.point(*q)
                        if self.contains(*point):
                            if previous is not None:d.line((previous,point),fill=altitude_color(p),width=5)
                            previous=point
                        else:previous=None
                draw_aircraft_symbol(d,x,y,self.heading(p),p.get('category',''),
                    altitude_color(p) if self.scene in ('map','map-island','map-ocean') else '#8f999f' if p.get('stale') else '#ff995e' if night else '#ed6a36',
                    getattr(self,'icon_outline','#b6c9d7' if night else 'white'),getattr(self,'icon_outline_width',2))
                if len(placed)>=getattr(self,'label_limit',1000):continue
                text=f"{p['callsign']}  {round(p['altitude_ft']/100)*100:,} ft";f=font(getattr(self,'label_size',42));w=d.textlength(text,font=f)+32
                box=label_box(x,y,w,occupied,getattr(self,'label_height',60),getattr(self,'label_gap',8))
                if box:
                    occupied.append(box);placed.append((box,text,f,x,y))
            for box,text,f,x,y in placed:
                lx,ly,rx,by=box
                anchor=(max(lx,min(rx,x)),max(ly,min(by,y)))
                d.line(((x,y),anchor),fill=getattr(self,'leader_color','#62707b'),width=getattr(self,'leader_width',2))
                d.rectangle(box,fill=label_bg,outline=getattr(self,'label_outline','#8c9ca6'),width=2)
                d.text((lx+12,ly+4),text,font=f,fill=label_fg)
        # Repaint every received hull above label layers, including zero-speed
        # reports. A group badge never substitutes for individual positions.
        if boats:self.vessel_symbols(d,boats,night)
        if data.get('theme',{}).get('show_info',True):
            d.rectangle((2700,108,3648,320),fill='#101c25')
            d.rectangle((2700,108,2706,320),fill='#ed6a36')
            d.text((2734,130),(('ATLANTIC APPROACHES' if self.scene=='map-ocean' else 'NEWFOUNDLAND AIRSPACE' if self.scene=='map-island' else 'AVALON AIRSPACE') if CONFIG.regional_preset=='newfoundland' else ('WIDE AREA AIRSPACE' if self.scene=='map-ocean' else 'REGIONAL AIRSPACE' if self.scene=='map-island' else 'LOCAL AIRSPACE')),font=font(58),fill='#f4f0e7')
            text=f"{visible} in view / {fresh_visible} fresh" if data['healthy'] else 'Receiver unavailable, last known positions'
            d.text((2734,231),text,font=fit(d,text,38,875,False,28),fill='#b6c5cf')
        attribution=getattr(self,'attribution','\u00a9 OpenStreetMap contributors')
        if attribution:
            f=font(34,False);w=d.textlength(attribution,font=f)+32
            d.rectangle((SAFE_RIGHT-w,1792,SAFE_RIGHT,1852),fill=label_bg);d.text((SAFE_RIGHT-w+16,1798),attribution,font=f,fill=label_fg)
        if self.status.get('missing_tiles'):
            d.text((SAFE_LEFT,1800),'Basemap partly unavailable',font=font(34,False),fill=label_fg)
        if self.scene in ('map','map-island','map-ocean'):
            d.rounded_rectangle((192,1710,2650,1852),radius=12,fill='#152635')
            d.text((220,1720),'ALTITUDE (ft) / GEOMETRIC   |   2-MINUTE TRAILS',font=font(33),fill='#c4d3dc')
            for i,(_,color,label) in enumerate((*BANDS,(0,'#8f999f','STALE'))):
                x=220+i*600;d.ellipse((x,1783,x+24,1807),fill=color)
                d.text((x+40,1772),label,font=font(35),fill='#f4f0e7')
        return image,visible

    def draw_vessels(self,d,data,occupied,night):
        groups=vessel_groups(data.get('vessels',[]),self.point,self.contains,self.scene=='map-island')
        rows=[v for g in groups for v in g['members']]
        visible=len(rows);labelled=[]
        fresh=sum(not v['stale'] for v in rows)
        moving=sum(not v['stale'] and (v.get('sog') or 0)>.5 for v in rows)
        budgets={'moving':8,'stationary':8,'group':4,'harbour':4};used=dict.fromkeys(budgets,0)
        # Independent stationary allowance; dense groups do not consume it.
        groups.sort(key=lambda g:('harbour' not in g,g['stale'],len(g['members'])>1,not g['moving'],g['members'][0]['mmsi']))
        for group in groups:
            v=group['members'][0];x,y=group['x'],group['y']
            color='#8b999d' if group['stale'] else '#37cfb8' if night else '#007d6e'
            count=len(group['members'])
            if count>1 and 'harbour' not in group:
                d.ellipse((x+18,y-55,x+72,y-1),fill='#12352f',outline='#ccf8e7',width=3)
                d.text((x+45,y-28),str(count),font=font(32),fill='#ffffff',anchor='mm')
            category='harbour' if 'harbour' in group else 'group' if count>1 else 'moving' if group['moving'] else 'stationary'
            if used[category]>=budgets[category]:continue
            text=(f'{count} VESSELS / SLOW OR UNKNOWN' if count>1 else
                  v['name'][:24]+('  '+f"{v['sog']:.1f} kn" if v.get('sog') is not None else ' / SPEED UNKNOWN'))
            if 'harbour' in group:text=f"HARBOUR / {count} "+('VESSEL' if count==1 else 'VESSELS')
            if count==1 and v.get('long_range'):text+=' / APPROX'
            f=font(38);box=label_box(x,y,d.textlength(text,font=f)+26,occupied,58,12)
            if box:
                occupied.append(box);labelled.append([m['mmsi'] for m in group['members']]);used[category]+=1
                d.line(((x,y),(max(box[0],min(box[2],x)),max(box[1],min(box[3],y)))),fill=color,width=2)
                d.rectangle(box,fill='#12352f' if night else '#e3f7ed',outline=color,width=2)
                d.text((box[0]+12,box[1]+5),text,font=f,fill='#e6fff5' if night else '#12352f')
        self.status['boats']={'in_view':visible,'fresh':fresh,'older':visible-fresh,'moving_fresh':moving,
                              'symbol_groups':len(groups),'individual_symbols':visible,'label_categories':used,'labelled_mmsi':[m for group in labelled for m in group],
                              'harbour_clusters':[{'area':g['harbour'],'vessels':len(g['members'])} for g in groups if 'harbour' in g]}
        d.rounded_rectangle((2700,344,3648,540),radius=10,fill='#12352f')
        state=(f'{visible} IN VIEW / {fresh} FRESH / {visible-fresh} OLDER' if visible else 'NO RECENT POSITIONS IN VIEW')
        d.text((2730,358),'BOATS / AISSTREAM',font=font(36),fill='#ccf8e7')
        d.text((2730,418),state,font=fit(d,state,32,888),fill='#ccf8e7')
        detail=f'{moving} MOVING VESSELS'
        if not data.get('connected'):detail='FEED RECONNECTING / LAST REPORTED POSITIONS'
        d.text((2730,473),detail,font=fit(d,detail,30,888),fill='#ccf8e7')
    def vessel_symbols(self,d,data,night):
        for v in data.get('vessels',[]):
            x,y=self.point(v['lat'],v['lon'])
            if not self.contains(x,y):continue
            color='#8b999d' if v['stale'] else '#37cfb8' if night else '#007d6e'
            previous=None
            for q in v.get('trail',[]):
                at=self.point(*q)
                if self.contains(*at):
                    if previous:d.line((previous,at),fill=color,width=3)
                    previous=at
                else:previous=None
            heading=v.get('heading')
            if heading is None:heading=v.get('cog') if (v.get('sog') or 0)>.5 else 0
            angle=math.radians(heading or 0);c=math.cos(angle);s=math.sin(angle)
            points=[(x+a*c-b*s,y+a*s+b*c) for a,b in ((0,-28),(12,-10),(12,23),(-12,23),(-12,-10))]
            d.polygon(points,fill=color);d.line(points+[points[0]],fill='#f2f2df',width=3)
    def tick(self):
        with self.lock:return self._tick()
    def ensure(self):
        if time.time()-self.status.get('updated_at',0)>1.5:self.tick()
    def _tick(self):
        if self.base is None or time.time()-self.built_at>7*86400:self.basemap()
        data=self.get_data();image,visible=self.draw(data)
        self.seq+=1;path=self.frames/f'frame-{time.time_ns()}.png'
        # These frames change every two seconds. Fast lossless compression avoids
        # rewriting an eight-megabyte bitmap while preserving text and alpha.
        frame=image.resize((1920,1080),Image.Resampling.LANCZOS)
        tmp=path.with_suffix('.tmp');frame.save(tmp,format='PNG',compress_level=1);tmp.replace(path)
        if playout.ENABLED:
            playout.command(f'LOADBG {self.channel}-10 "/workspace/runtime/{self.scene}/{path.name}"')
            playout.command(f'PLAY {self.channel}-10');playout.heartbeat(self.scene)
        preview=self.frames/'preview.tmp';frame.convert('RGB').save(preview,format='JPEG',quality=88);preview.replace(self.frames/'preview.jpg')
        self.status.update(ready=True,error=None,updated_at=time.time(),aircraft_in_view=visible,receiver_healthy=data['healthy'],theme=data.get('theme',{}).get('effective','day'))
        for old in sorted(self.frames.glob('frame-*.*'))[:-4]:old.unlink(missing_ok=True)
    async def watch(self):
        if not playout.ENABLED:return
        while True:
            started=time.monotonic()
            try:
                needed={playout.STATUS.get('program',{}).get('camera'),(playout.STATUS.get('preview') or {}).get('camera')}
                if not self.status.get('ready') or self.scene in needed:await asyncio.to_thread(self.tick)
            except Exception as exc:self.status.update(ready=False,error=str(exc)[:200])
            await asyncio.sleep(max(.1,2-(time.monotonic()-started)))
