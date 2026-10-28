from .station_config import CONFIG
from .branding import BRAND
"""Lightweight native information boards, prepared in the existing scene banks."""
import asyncio, hashlib, json, threading, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageDraw
from . import daylight
from .graphics import brand, font, fit, PAPER, ORANGE
from .image_cache import valid_image

SCENES = ('marine', 'moon', 'daylight', 'station-info', 'yyt-arrivals', 'yyt-departures', 'community-notices', 'community-calendar', 'markets', 'tides', 'power-outages', 'power-supply', 'power-history', 'power-report', 'weather-timeline', 'nl-travel', 'harbour-watch', 'tonights-sky', 'morning-briefing', 'evening-briefing')
MUTED = '#b4c9d5'

def clock(value):
    return datetime.fromisoformat(value).strftime('%I:%M %p').lstrip('0')

def heading(title, subtitle):
    im=Image.new('RGB',(3840,2160),'#0e1e29');d=ImageDraw.Draw(im)
    brand(d,192,108)
    d.text((192,310),title,font=font(124),fill=PAPER)
    d.text((196,466),subtitle,font=font(42,False),fill=MUTED)
    d.rectangle((192,555,3648,563),fill=ORANGE)
    return im,d

def daylight_image(data):
    e=data['events'];day=datetime.fromisoformat(data['calculated_at']).astimezone(daylight.TZ)
    im,d=heading('DAYLIGHT & SKY',CONFIG.location.name.upper()+'  /  '+day.strftime('%A, %B %d').upper()+ '  /  '+day.tzname())
    for x,label,key in [(192,'SUNRISE','sunrise'),(1360,'SUNSET','sunset')]:
        d.rounded_rectangle((x,620,x+1104,995),radius=22,fill='#203643')
        d.text((x+48,660),label,font=font(60),fill='#ffb578')
        d.text((x+48,760),clock(e[key]),font=font(150),fill=PAPER)
    mins=round(data['daylight_seconds']/60);change=round(abs(data['change_seconds'])/60)
    d.text((2580,650),'TODAY\'S DAYLIGHT',font=font(52),fill='#ffb578')
    d.text((2580,744),f'{mins//60}h {mins%60:02d}m',font=font(168),fill=PAPER)
    delta='About the same as yesterday' if change==0 else f'{change} min '+('more' if data['change_seconds']>0 else 'less')+' than yesterday'
    d.text((2580,963),delta,font=fit(d,delta,44,1068,False),fill=MUTED)
    for x,key,label in [(192,'moonrise','MOONRISE'),(1360,'moonset','MOONSET')]:
        event=daylight.lunar_display(data,key)
        d.rounded_rectangle((x,1015,x+1104,1115),radius=14,fill='#193748')
        d.text((x+25,1022),('NEXT ' if event['next'] else '')+label,font=font(34),fill='#9fdcff')
        d.text((x+380,1020),event['time'],font=font(54),fill=PAPER)
        d.text((x+25,1070),event['date'],font=font(28,False),fill=MUTED)
    # Same time/elevation axes for both bodies, including the below-horizon night.
    left,right,top,bottom=290,2370,1230,1640
    points=data['sky_curve'];start,end=points[0]['at'],points[-1]['at']
    xy=lambda at,alt:(left+(right-left)*(at-start)/(end-start),bottom-(bottom-top)*(alt+90)/180)
    horizon=xy(start,0)[1]
    d.text((192,1145),'TODAY IN THE SKY',font=font(48),fill=PAPER)
    d.text((1250,1145),'SUN',font=font(44),fill='#ffb578')
    d.text((1500,1145),'MOON',font=font(44),fill='#9fdcff')
    d.rectangle((left,horizon,right,bottom),fill='#142530')
    for alt in (-90,-45,0,45,90):
        y=xy(start,alt)[1]
        d.line((left,y,right,y),fill='#536c7c' if alt==0 else '#273e4b',width=3 if alt==0 else 1)
        d.text((194,y-18),str(alt)+'°',font=font(29,False),fill=MUTED)
    for hour in (0,6,12,18,24):
        at=(day.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(hours=hour)).timestamp()
        x=xy(at,0)[0]
        d.line((x,top,x,bottom),fill='#273e4b',width=1)
        text={0:'MIDNIGHT',6:'6 AM',12:'NOON',18:'6 PM',24:'MIDNIGHT'}[hour]
        d.text((x-d.textlength(text,font=font(32,False))/2,bottom+18),text,font=font(32,False),fill=MUTED)
    for body,color in [('sun','#ffb578'),('moon','#9fdcff')]:
        d.line([xy(p['at'],p[body]) for p in points],fill=color,width=8)
    now=day.timestamp();x=xy(now,0)[0]
    d.line((x,top,x,bottom),fill='#e7e7de',width=2)
    d.text((max(left,min(x-55,right-110)),top-48),'NOW',font=font(34),fill=PAPER)
    for key,color in [('solar_elevation','#ffb578'),('moon_elevation','#9fdcff')]:
        x,y=xy(now,data[key]);d.ellipse((x-19,y-19,x+19,y+19),fill=color,outline=PAPER,width=3)
    d.text((right+18,horizon-20),'HORIZON',font=font(28),fill=MUTED)
    compass=lambda angle:('N','NE','E','SE','S','SW','W','NW')[int((angle+22.5)//45)%8]
    for y,label,el,az,color in [(1130,'SUN NOW',data['solar_elevation'],data['solar_azimuth'],'#ffb578'),
                               (1420,'MOON NOW',data['moon_elevation'],data['moon_azimuth'],'#9fdcff')]:
        d.text((2580,y),label,font=font(48),fill=color)
        d.text((2580,y+65),f'{abs(el):.0f}° '+('above' if el>=0 else 'below'),font=font(100),fill=PAPER)
        d.text((2580,y+180),f'HORIZON  /  {compass(az)} {az:.0f}°',font=font(40,False),fill=MUTED)
    d.text((192,1865),'ASTRAL',font=font(30,False),fill=MUTED)
    return im

def station_image():
    im,d=heading(BRAND.station_name, CONFIG.location.name.upper())
    cards=[('CAMERAS',"St. John's & the Avalon",'Live local views',''),
           ('AIRSPACE','Aircraft & vessels','Local aircraft coverage and received vessel positions',''),
           ('WEATHER','Forecasts & radar','Local weather and alerts','')]
    for i,(tag,title,line1,line2) in enumerate(cards):
        y=630+i*365
        d.rounded_rectangle((192,y,3648,y+310),radius=22,fill='#203643')
        d.rectangle((192,y,205,y+310),fill=ORANGE)
        d.text((250,y+35),tag,font=font(52),fill='#ffb578')
        d.text((250,y+115),title,font=font(90),fill=PAPER)
        d.text((1460,y+62),line1,font=fit(d,line1,56,2090,False),fill=PAPER)
        d.text((1460,y+158),line2,font=fit(d,line2,48,2090,False),fill=MUTED)
    d.text((192,1804),'WATCH ON YOUTUBE',font=font(48),fill='#ffb578')
    d.text((950,1785),BRAND.website,font=font(76),fill=PAPER)
    return im

def flight_image(data,page):
    direction=data['direction'];rows=data['rows'];pages=max(1,(len(rows)+5)//6)
    checked=datetime.fromtimestamp(data['checked_at'],daylight.TZ).strftime('%b %d, %I:%M %p %Z') if data.get('checked_at') else 'WAITING FOR FIRST CHECK'
    status='CACHED / CHECKED ' if data.get('cached') else 'CHECKED '
    im,d=heading('YYT / '+direction.upper(),"ST. JOHN'S INTERNATIONAL AIRPORT  /  "+status+checked.upper())
    if not data['available']:
        d.text((240,860),'FLIGHT INFORMATION UNAVAILABLE',font=font(120),fill=PAPER)
    elif not rows:
        d.text((240,860),'NO SCHEDULED FLIGHTS IN THIS WINDOW',font=font(116),fill=PAPER)
    else:
        for x,label in [(250,'FLIGHT / AIRLINE'),(960,'FROM' if direction=='arrivals' else 'TO'),(2100,'SCHEDULED'),(2460,'REVISED'),(2850,'STATUS')]:
            d.text((x,632),label,font=font(42),fill='#ffb578')
        for i,row in enumerate(rows[page*6:page*6+6]):
            y=730+i*165
            d.rounded_rectangle((192,y,3648,y+145),radius=12,fill='#203643' if i%2==0 else '#182b36')
            d.text((250,y+12),row['flight-num'],font=font(72),fill=PAPER)
            d.text((250,y+95),row['airline'],font=fit(d,row['airline'],34,640,False),fill=MUTED)
            d.text((960,y+30),row['city'],font=fit(d,row['city'],74,1060,False),fill=PAPER)
            d.text((2100,y+16),row['time'],font=font(70),fill=PAPER)
            d.text((2100,y+98),row['date'],font=font(32,False),fill=MUTED)
            d.text((2460,y+26),row['revised'] or '--',font=font(70),fill=PAPER if row['revised'] else MUTED)
            color='#ffb578' if any(s in row['status'].lower() for s in ('cancel','delay')) else '#a8d9c2'
            d.text((2850,y+35),row['status'],font=fit(d,row['status'],62,740,False),fill=color)
    d.text((192,1775),"ST. JOHN'S INTERNATIONAL AIRPORT / NEWFOUNDLAND TIME / CHECK WITH AIRLINE",font=font(36,False),fill=MUTED)
    if pages>1:d.text((3260,1844),f'PAGE {page+1} / {pages}',font=font(42),fill='#ffb578')
    return im

class CommunityCards:
    def __init__(self,data,flights=None,notices=None,markets=None,tides=None,outages=None):
        self.marine=None;self.power_system=None;self.power_reports=None;self.weather=None;self.travel=None;self.ais=None;self.space_weather=None;self.market_timing=lambda:None
        self.folder=Path(data)/'runtime'/'community-cards';self.folder.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.status={};self.flights=flights;self.notices=notices;self.markets=markets;self.tides=tides;self.outages=outages;self.outage_map=None
    def path(self,scene,now=None,page_override=None):
        if scene not in SCENES:raise ValueError('Unknown information board')
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:raise ValueError('Information boards require an aware datetime')
        # Shared minute cache for previews and program. No full-rate renderer.
        data=daylight.public(now.replace(second=0,microsecond=0)) if scene=='daylight' else None
        if scene=='moon':
            from .moon_card import public as moon_public
            data=moon_public(now)
        page=0
        if scene=='marine':
            data=self.marine.public(now.timestamp()) if self.marine else {'groups':[],'available':False,'cached':False}
            from .marine import pages
            page=(int(now.timestamp()//18) if page_override is None else page_override)%max(1,len(pages(data)))
        if scene=='power-supply':data=self.power_system.public(now.timestamp()) if self.power_system else {'readings':[],'minute':int(now.timestamp()//60)}
        if scene in ('power-history','power-report'):data=self.power_reports.public() if self.power_reports else {'latest':None}
        if scene=='power-outages':
            data=self.outages.public(now.timestamp()) if self.outages else {'active':[],'fresh':False,'checked_at':0,'minute':int(now.timestamp()//60)}
            pages=max(1,(len(data['active'])+len(data.get('upcoming',[]))+2)//3)
            # Rotate the starting page each quarter-hour so a busy outage list
            # is not permanently hidden behind the first minute of coverage.
            page=(int(now.timestamp()//900)*3+(int(now.timestamp()//18) if page_override is None else page_override))%pages
        if scene=='tides':data=self.tides.public(now.timestamp()) if self.tides else {'events':[],'checked_at':0,'cached':True}
        if scene=='markets':
            data=self.markets.public(now.timestamp()) if self.markets else {'cards':[]}
            page=(int(now.timestamp()//10) if page_override is None else page_override)%3
        if scene=='community-notices':
            data=notice_pages(self.notices.active() if self.notices else [])
            page=(int(now.timestamp()//20) if page_override is None else page_override)%max(1,len(data))
        if scene=='community-calendar':data=self.notices.public(now)['items'] if self.notices else []
        if scene=='weather-timeline':data=self.weather.public(now.timestamp()) if self.weather else {'forecast_available':False}
        if scene=='nl-travel':data=self.travel.public(now.timestamp()) if self.travel else {'available':False}
        if scene=='harbour-watch':data={'ais':self.ais.public(now.timestamp()) if self.ais else {},'tides':self.tides.public(now.timestamp()) if self.tides else {},'marine':self.marine.public(now.timestamp()) if self.marine else {}}
        if scene=='tonights-sky':
            from .moon_card import public as moon_public
            data={'daylight':daylight.public(now),'moon':moon_public(now),'weather':self.weather.public(now.timestamp()) if self.weather else {},'space':self.space_weather.public(now.timestamp()) if self.space_weather else {},'location':CONFIG.location.name}
        if scene in ('morning-briefing','evening-briefing'):
            data={'weather':self.weather.public(now.timestamp()) if self.weather else {},'travel':self.travel.public(now.timestamp()) if self.travel else {},'outages':self.outages.public(now.timestamp()) if self.outages else {},'location':CONFIG.location.name}
        if scene.startswith('yyt-'):
            direction=scene.split('-',1)[1]
            data=self.flights.public(direction,now.timestamp()) if self.flights else {'direction':direction,'rows':[],'available':False,'checked_at':None}
            pages=max(1,(len(data['rows'])+5)//6)
            page=(int(now.timestamp()//18) if page_override is None else page_override)%pages
        key=hashlib.sha256(json.dumps([scene,data,page,'v5-composite-screens'],sort_keys=True).encode()).hexdigest()[:24]
        with self.lock:
            path=self.folder/(scene+'-'+key+'.png')
            if not valid_image(path,(3840,2160)):
                from .moon_card import image as moon_image
                from .marine import image as marine_image
                from .tides import image as tides_image
                from .outages import outage_image
                from .power_system import image as power_image
                from .power_report_graphics import image as report_image
                from .information_graphics import weather_timeline_image,travel_image,harbour_image,sky_image,briefing_image,calendar_image
                im=(weather_timeline_image(data) if scene=='weather-timeline' else travel_image(data) if scene=='nl-travel' else harbour_image(data) if scene=='harbour-watch' else sky_image(data) if scene=='tonights-sky' else briefing_image(data,'morning' if scene=='morning-briefing' else 'evening') if scene in ('morning-briefing','evening-briefing') else calendar_image(data,now) if scene=='community-calendar' else report_image(data,scene) if scene in ('power-history','power-report') else power_image(data) if scene=='power-supply' else marine_image(data,page) if scene=='marine' else moon_image(data) if scene=='moon' else outage_image(data,page,self.outage_map) if scene=='power-outages' else tides_image(data) if scene=='tides' else markets_image(data,page) if scene=='markets' else notice_image(data[page] if data else None,self.notices.assets if self.notices else None) if scene=='community-notices' else flight_image(data,page) if scene.startswith('yyt-') else daylight_image(data) if data else station_image())
                temp=path.with_suffix('.tmp');im.save(temp,format='PNG',compress_level=1);temp.replace(path)
            # Bounded runtime RAM cache. Keep recent assets for both scene banks.
            others=[p for p in self.folder.glob(scene+'-*.png') if p!=path]
            for old in sorted(others,key=lambda p:p.stat().st_mtime)[:-15]:
                old.unlink(missing_ok=True)
            return path
    def warm_outage_map(self):
        from .map_renderer import MapRenderer
        from .outages import display_rows
        rows=display_rows(self.outages.public())
        wide=any(r.get('lat') is not None and (r['lat']>51.5 or r['lon']<-60) for r in rows)
        center,zoom=((54,-60),5) if wide else ((49,-56),7)
        current=self.outage_map
        if current and current.center==center and current.zoom==zoom and time.time()-current.built_at<86400:return
        replacement=MapRenderer(self.folder.parent.parent,lambda:{},'outage-map',center=center,zoom=zoom,view_scale=1.2)
        replacement.basemap()
        with self.lock:self.outage_map=replacement
    def media(self,scene):return '/workspace/runtime/community-cards/'+self.path(scene).name
    def prepare_media(self,scene):return '/workspace/runtime/community-cards/'+self.path(scene,page_override=0).name
    async def watch(self):
        from . import playout
        previous=None;onair=None;started=0;last_rendered=0;last_page=None
        while True:
            try:
                scene=playout._camera
                if playout.STATUS.get('ready') and scene in SCENES:
                    bank=playout._bank
                    if onair!=(scene,bank):
                        onair=(scene,bank);started=time.monotonic();last_rendered=0;last_page=None
                    elapsed=time.monotonic()-started
                    page=int(elapsed//18)
                    if scene=='markets':
                        timing=self.market_timing()
                        page=market_page(timing['elapsed'] if timing else elapsed,timing['seconds'] if timing else None)
                        if last_page==page and time.monotonic()-last_rendered<5:
                            await asyncio.sleep(.5);continue
                    asset=await asyncio.to_thread(self.path,scene,page_override=page)
                    path='/workspace/runtime/community-cards/'+asset.name
                    if path!=previous:
                        with playout.LOCK:
                            if (playout._camera,playout._bank)==(scene,bank):
                                playout.command(f'PLAY {playout._bank}-10 "{path}"');previous=path
                    last_rendered=time.monotonic();last_page=page
                    self.status={'scene':scene,'page':page,'error':None}
                else:previous=None;onair=None
            except Exception as exc:self.status={'error':str(exc)[:180]};previous=None
            await asyncio.sleep(.5 if scene=='markets' else 5)

def notice_pages(items):
    from .alert_graphics import wrap
    rows=[]
    for item in items:
        lines=wrap(item['text'],76,2610 if item.get('url') else 3230)
        chunks=[lines[i:i+8] for i in range(0,len(lines),8)] if item['text'].strip() else []
        total=len(chunks)+bool(item.get('image_id'))
        if item.get('image_id'):rows.append({'notice':item,'image':True,'lines':[],'part':1,'parts':total})
        for i,chunk in enumerate(chunks):rows.append({'notice':item,'lines':chunk,'part':i+1+bool(item.get('image_id')),'parts':total})
    return rows

def notice_image(row,assets=None):
    im,d=heading('COMMUNITY NOTICEBOARD','LOCAL INFORMATION')
    if row is None:
        d.text((240,850),'NO CURRENT NOTICES',font=font(124),fill=PAPER)
        return im
    if row.get('image'):
        n=row['notice'];d.text((192,595),n['title'],font=fit(d,n['title'],78,3456),fill=PAPER)
        from PIL import ImageOps
        path=assets/(n['image_id']+'.png') if assets else None
        if path and path.is_file():
            with Image.open(path) as source:picture=ImageOps.contain(source.convert('RGB'),(3456,1050),Image.Resampling.LANCZOS)
            im.paste(picture,(192+(3456-picture.width)//2,720+(1050-picture.height)//2))
        else:d.text((240,1040),'NOTICE IMAGE UNAVAILABLE',font=font(104),fill=PAPER)
        d.text((192,1840),n.get('credit') or 'COMMUNITY INFORMATION',font=fit(d,n.get('credit') or 'COMMUNITY INFORMATION',38,3000,False),fill=MUTED)
        return im
    n=row['notice'];d.rounded_rectangle((192,625,3648,1770),radius=22,fill='#203643')
    d.text((270,678),n['title'],font=fit(d,n['title'],112,3300),fill=PAPER)
    d.text((270,840),n['location'],font=fit(d,n['location'],48,3300,False),fill='#ffb578')
    for i,line in enumerate(row['lines']):d.text((270,955+i*92),line,font=font(76,False),fill=PAPER)
    if n.get('url'):
        import cv2
        from PIL import ImageOps
        code=ImageOps.expand(Image.fromarray(cv2.QRCodeEncoder_create().encode(n['url'])),border=4,fill=255)
        side=(480//code.width)*code.width;code=code.resize((side,side),Image.Resampling.NEAREST)
        im.paste(code,(3040+(480-side)//2,1080))
        d.text((3040,1615),'SCAN FOR DETAILS',font=font(40),fill=PAPER)
    label='COMMUNITY INFORMATION'
    if n.get('ends_at'):
        end=datetime.fromisoformat(n['ends_at']).astimezone(daylight.TZ)
        label+=' / DISPLAY UNTIL '+end.strftime('%b %d, %I:%M %p %Z').upper()
    d.text((192,1840),label,font=fit(d,label,36,2850,False),fill=MUTED)
    if row['parts']>1:d.text((3260,1836),f"PAGE {row['part']} / {row['parts']}",font=font(42),fill='#ffb578')
    return im


def market_page(elapsed,seconds=None):
    return min(2,int(max(0,elapsed)/(max(1,seconds)/3))) if seconds is not None else int(max(0,elapsed)//10)%3

def markets_image(data,page=0):
    from .market_graphics import image,grid_image
    return image(data) if page%3==0 else grid_image(data,page%3)
