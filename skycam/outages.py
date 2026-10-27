"""Independent utility outage feeds; planned work never enters emergency presentation."""
from .bounded_http import bounded_get
from .public_errors import public_error
import asyncio, hashlib, html, json, math, re, threading, time
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from pydantic import Field
from PIL import Image, ImageDraw
from .models import StrictModel
from .storage import save_json
from .graphics import font, fit, PAPER

SOURCE='https://services1.arcgis.com/X4jBywOcHsB7HKqU/arcgis/rest/services/Public_Outage_Map_Prod/FeatureServer'
PUBLIC_URL='https://www.newfoundlandpower.com/Outages/Outage-Map'
TZ=ZoneInfo('America/St_Johns')
FRESH_SECONDS=1200
HYDRO_URL='https://my.nlhydro.com/outage/'
HYDRO_FEEDS={'hydro-current':HYDRO_URL+'json/GetOutageSummery_C.json','hydro-planned':HYDRO_URL+'json/GetOutageSummery_P.json'}

class OutageConfig(StrictModel):
    banner_enabled:bool=True
    banner_seconds:int=Field(default=30,ge=15,le=90)
    repeat_minutes:int=Field(default=10,ge=5,le=60)

def clean(value,limit=600):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',str(value or '')))).strip()[:limit]

def stamp(value):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Invalid outage date')
    # ArcGIS dates are milliseconds since UTC epoch. Reject sentinel dates.
    return value/1000 if 946684800000<=value<=4102444800000 else None

def is_planned(row):
    cause=clean(row.get('cause') or row.get('Title')).casefold()
    return bool(row.get('planned')) or bool(re.search(r'\b(?:scheduled|planned)\s+(?:maintenance|work|outage|power interruption)\b',cause))

def deduplicate_planned(rows):
    result=[]
    # A currently executing scheduled job may occur in both utility datasets.
    # Merge only exact location/provider matches with matching one-hour windows.
    for row in sorted(rows,key=lambda r:(not r.get('fresh',False),not r.get('feed','').endswith('-planned'))):
        duplicate=next((r for r in result if is_planned(row) and is_planned(r)
            and r.get('provider')==row.get('provider') and r['location'].casefold()==row['location'].casefold()
            and r.get('feed')!=row.get('feed') and abs(r['start']-row['start'])<3600
            and r.get('estimate') is not None and row.get('estimate') is not None and abs(r['estimate']-row['estimate'])<3600),None)
        if duplicate is None:result.append(row)
    return result

def parse(features,planned,now):
    rows={}
    for feature in features:
        a=feature['attributes'];identifier=a['ID'];count=a['CUSTOMER_COUNT']
        if not isinstance(identifier,int) or isinstance(count,bool) or not isinstance(count,(int,float)) or not math.isfinite(count) or count<0:raise ValueError('Invalid outage record')
        start=stamp(a.get('TIME_BEGIN' if planned else 'TIME_OUTAGE'))
        end=stamp(a.get('TIME_END' if planned else 'TIME_RESTORED_EST'))
        if count==0:continue
        if start is None:raise ValueError('Outage start is missing')
        if not planned and start>now+300:raise ValueError('Unplanned outage starts in the future')
        g=feature.get('geometry') or {};lon=g.get('x');lat=g.get('y')
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (lat,lon)) or not (45<=lat<=62 and -68<=lon<=-50):lat=lon=None
        key=('planned-' if planned else 'unplanned-')+str(identifier)
        rows[key]={'id':key,'planned':planned or is_planned({'cause':a.get('CAUSE')}),'start':start,'estimate':end,'customers':int(count),
            'provider':'Newfoundland Power','feed':'nlpower-planned' if planned else 'nlpower-current',
            'location':clean(a.get('POLYGONS_AFFECTED')) or 'Location not supplied',
            'cause':clean(a.get('CAUSE')) or 'Under investigation','crew':clean(a.get('CREW_STATUS')),
            'remarks':clean(a.get('REMARKS' if planned else 'NLP_ALERT_REMARKS')),'lat':lat,'lon':lon}
    return list(rows.values())

async def fetch_layer(client,layer):
    meta=await bounded_get(client,f'{SOURCE}/{layer}',params={'f':'json'})
    meta.raise_for_status();metadata=meta.json()
    edited=stamp(metadata.get('editingInfo',{}).get('dataLastEditDate'))
    if edited is None or not -300<=time.time()-edited<3600:raise ValueError('Utility dataset has not updated recently')
    if metadata.get('dateFieldsTimeReference',{}).get('timeZone')!='UTC':raise ValueError('Utility date reference changed')
    rows=[];seen=set()
    for offset in range(0,5000,500):
        response=await bounded_get(client,f'{SOURCE}/{layer}/query',max_bytes=4_000_000,params={'f':'json','where':'1=1','outFields':'*','outSR':4326,
            'returnGeometry':'true','orderByFields':'OBJECTID','resultOffset':offset,'resultRecordCount':500},headers={'Cache-Control':'no-cache'})
        response.raise_for_status()
        if len(response.content)>4_000_000:raise ValueError('Outage response too large')
        data=response.json()
        if 'error' in data or not isinstance(data.get('features'),list):raise ValueError('Outage service returned an invalid response')
        if data.get('spatialReference',{}).get('wkid',4326) not in (4326,):raise ValueError('Outage map coordinate system changed')
        batch=data['features']
        for f in batch:
            oid=f['attributes']['OBJECTID']
            if oid in seen:raise ValueError('Outage pagination repeated a record')
            seen.add(oid)
        rows.extend(batch)
        if not data.get('exceededTransferLimit'):return rows
        if not batch:raise ValueError('Outage pagination incomplete')
    raise ValueError('Outage result exceeds bounded page limit')

def hydro_stamp(value):
    if not value:return None
    dt=datetime.fromisoformat(str(value))
    if dt.tzinfo is None:dt=dt.replace(tzinfo=TZ)
    value=dt.timestamp()
    if not 946684800<=value<=4102444800:raise ValueError('Invalid Hydro outage date')
    return value

def parse_hydro(records,planned,now):
    if not isinstance(records,list) or len(records)>2000:raise ValueError('Invalid Hydro outage list')
    rows={}
    for a in records:
        identifier=a.get('Outageid')
        if type(identifier) is not int or identifier<0:raise ValueError('Invalid Hydro outage identifier')
        count=a.get('CustomerAffected')
        if count is not None and (type(count) not in (int,float) or not math.isfinite(count) or count<0):raise ValueError('Invalid Hydro customer count')
        # Preserve the published count, including zero; zero does not suppress a notice.
        count=int(count) if count is not None else None
        start=hydro_stamp(a.get('OutagedateDB'));end=hydro_stamp(a.get('RestorationdateDB'))
        if planned and start is None:raise ValueError('Hydro planned start is missing')
        if not planned and start and start>now+300:raise ValueError('Hydro current outage starts in the future')
        lat=a.get('OutageLatitude');lon=a.get('OutageLongitude')
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (lat,lon)) or not (45<=lat<=62 and -68<=lon<=-50):lat=lon=None
        key='hydro-'+('planned-' if planned else 'unplanned-')+str(identifier)
        location=clean(a.get('CommunityName') or a.get('Towns') or a.get('Header')) or 'Location not supplied'
        rows[key]={'id':key,'provider':'Newfoundland & Labrador Hydro','feed':'hydro-planned' if planned else 'hydro-current',
          'planned':planned or is_planned(a),'start':start or 0,'estimate':end,'customers':count,'location':location,
          'cause':clean(a.get('Title')) or 'Under investigation','crew':'',
          'remarks':clean(a.get('OutageReportInfo'),1500),'lat':lat,'lon':lon}
    return list(rows.values())

async def fetch_hydro(client,planned,now):
    url=HYDRO_FEEDS['hydro-planned' if planned else 'hydro-current']
    async with client.stream('GET',url,headers={'Accept':'application/json','Cache-Control':'no-cache'}) as response:
        response.raise_for_status();raw=bytearray()
        async for part in response.aiter_bytes():
            raw.extend(part)
            if len(raw)>4_000_000:raise ValueError('Hydro outage response too large')
    return parse_hydro(json.loads(raw),planned,now)

def customer_text(row):
    if row.get('customers')==0:return ''
    return f"{row['customers']:,} customers" if row.get('customers') is not None else 'Customer count not provided'

def display_rows(data):
    return data.get('active',[])+data.get('upcoming',[])

class Outages:
    def __init__(self,data,enabled=True):
        self.enabled=enabled
        self.folder=data/'broadcast';self.path=self.folder/'outages.json';self.cache=self.folder/'outages-cache.json'
        self.lock=threading.RLock();self.rows=[];self.checked_at=0;self.error=None;self.banner_key=None;self.banner_at=0
        self.config=OutageConfig.model_validate_json(self.path.read_text()) if self.path.exists() else OutageConfig()
        # Always verify the live service after boot before announcing cached incidents.
        self.verified=False;self.feed_status={}
        try:
            if self.enabled:
                c=json.loads(self.cache.read_text());self.rows=c['rows'];self.checked_at=c['checked_at']
        except (OSError,ValueError,KeyError):pass
    def save(self,body):
        with self.lock:save_json(self.path,body.model_dump());self.config=body
    async def refresh(self):
        if not self.enabled:return
        now=time.time()
        async def power(client,planned):return parse(await fetch_layer(client,int(planned)),planned,now)
        names=('nlpower-current','nlpower-planned','hydro-current','hydro-planned')
        async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
            results=await asyncio.gather(power(client,False),power(client,True),fetch_hydro(client,False,now),fetch_hydro(client,True,now),return_exceptions=True)
        with self.lock:
            for name,result in zip(names,results):
                prior=self.feed_status.get(name,{'checked_at':0,'verified':False})
                if isinstance(result,Exception):
                    self.feed_status[name]={**prior,'error':str(result)[:180]}
                    continue
                self.rows=[r for r in self.rows if r.get('feed',('nlpower-planned' if r['planned'] else 'nlpower-current'))!=name]+result
                self.feed_status[name]={'checked_at':now,'verified':True,'error':None}
            self.checked_at=max((v['checked_at'] for v in self.feed_status.values()),default=0)
            self.verified=any(v['verified'] for v in self.feed_status.values())
            self.error='; '.join(k+': '+v['error'] for k,v in self.feed_status.items() if v.get('error')) or None
            save_json(self.cache,{'rows':self.rows,'checked_at':self.checked_at})
    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            fresh=self.verified and 0<=now-self.checked_at<FRESH_SECONDS and self.error is None
            feeds={k:{**v,'fresh':v.get('verified',False) and not v.get('error') and 0<=now-v['checked_at']<FRESH_SECONDS} for k,v in self.feed_status.items()}
            if feeds:fresh=any(v['fresh'] for v in feeds.values())
            rows=[{**r,'fresh':feeds.get(r.get('feed','nlpower-planned' if r['planned'] else 'nlpower-current'),{}).get('fresh',fresh)} for r in self.rows]
            # Planned windows expire; an elapsed unplanned estimate does not prove restoration.
            rows=deduplicate_planned(rows)
            rows=[r for r in rows if not (r['planned'] and r['estimate'] and r['estimate']<=now)]
            active=sorted([r for r in rows if r['start']<=now],key=lambda r:(r['planned'],-(r['customers'] or 0),r['id']))
            upcoming=sorted([r for r in rows if r['planned'] and now<r['start']<now+7*86400],key=lambda r:r['start'])
            return {'config':self.config.model_dump(),'fresh':fresh,'complete':all(v['fresh'] for v in feeds.values()) if feeds else fresh,
                'feeds':feeds,'checked_at':self.checked_at,'error':self.error,
                'active':active,'upcoming':upcoming,'customers':sum(r['customers'] or 0 for r in active),
                'unknown_customer_counts':sum(r['customers'] is None for r in active),'source':SOURCE,'url':PUBLIC_URL,'hydro_url':HYDRO_URL,
                'coverage':'Newfoundland Power public map (25+ customers) and Newfoundland & Labrador Hydro public notices',
                'minute':int(now//60)}
    def eligible(self):
        d=self.public();return any(r.get('fresh',d['fresh']) for r in display_rows(d))
    def banner(self,now=None):
        now=time.time() if now is None else now;d=self.public(now)
        rows=[r for r in d['active'] if not is_planned(r) and r.get('fresh',d['fresh'])]
        if not d['fresh'] or not rows or not self.config.banner_enabled:return None
        key=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        with self.lock:
            if key!=self.banner_key or now-self.banner_at>=self.config.repeat_minutes*60:
                self.banner_key=key;self.banner_at=now
            if now-self.banner_at>=self.config.banner_seconds:return None
            row=rows[int((now-self.banner_at)//10)%len(rows)]
            return {'row':row,'total':len(rows),'customers':sum(r['customers'] or 0 for r in rows),'checked_at':d['checked_at'],'minute':d['minute']}
    async def watch(self):
        while True:
            try:await self.refresh()
            except Exception as exc:
                with self.lock:self.error=public_error(exc)[:180]
            # Network tile acquisition never holds the scene-take or music lock.
            if self.eligible() and getattr(self,'warm_map',None):
                try:await asyncio.to_thread(self.warm_map)
                except Exception:pass  # Incident text remains usable without map tiles.
            await asyncio.sleep(300)

def local_time(value):
    return datetime.fromtimestamp(value,TZ).strftime('%b %d, %I:%M %p %Z').replace(' 0',' ') if value else 'Not yet available'

def planned_window(row):
    start=datetime.fromtimestamp(row['start'],TZ)
    text=start.strftime('%b %d, %I:%M %p').replace(' 0',' ')
    if row.get('estimate'):
        end=datetime.fromtimestamp(row['estimate'],TZ)
        text+=' TO '+end.strftime('%I:%M %p %Z' if start.date()==end.date() else '%b %d, %I:%M %p %Z').replace(' 0',' ')
    return text

def restoration(row,now):
    end=row['estimate']
    return 'Awaiting revised estimate' if end and end<now else local_time(end)

def banner_image(data):
    r=data['row'];im=Image.new('RGB',(3840,224),'#f4ca71');d=ImageDraw.Draw(im)
    d.rectangle((0,0,3840,7),fill='#ba7223')
    d.text((192,24),'POWER OUTAGE UPDATE',font=font(55),fill='#17232c')
    text=' / '.join(part for part in (customer_text(r),r['location']) if part)
    text=shorten(text,52,2658)
    d.text((990,15),text,font=fit(d,text,65,2658,False),fill='#17232c')
    line='Estimated restoration: '+restoration(r,data['minute']*60)+'  /  '+r.get('provider','Newfoundland Power')
    d.text((990,110),line,font=fit(d,line,52,2658,False),fill='#17232c')
    d.text((192,114),'UTILITY INFORMATION',font=font(35),fill='#483b2a')
    return im

def shorten(text,size,width):
    f=font(size,False)
    if f.getlength(text)<=width:return text
    while text and f.getlength(text+'...')>width:text=text[:-1]
    return text.rstrip()+'...'

def outage_image(data,page,basemap=None):
    from .community_cards import heading,MUTED
    from .alert_graphics import wrap
    im,d=heading('POWER OUTAGE UPDATE','NL POWER + NL HYDRO  /  '+('CHECKED '+local_time(data['checked_at']).upper() if data.get('complete',data['fresh']) else 'SOME SOURCES UNAVAILABLE' if data['fresh'] else 'CURRENT STATUS UNAVAILABLE'))
    rows=display_rows(data);pages=max(1,(len(rows)+2)//3);page%=pages
    if not data['fresh'] or not rows:
        title=('NO CURRENT OUTAGES REPORTED' if data.get('complete',True) else 'NO INCIDENTS IN AVAILABLE FEEDS') if data['fresh'] else 'OUTAGE INFORMATION UNAVAILABLE'
        d.text((240,800),title,font=fit(d,title,128,3360),fill=PAPER)
    else:
        left,top,w,h=192,630,2148,1208
        if basemap and basemap.base:
            im.paste(basemap.base.convert('RGB').resize((w,h),Image.Resampling.LANCZOS),(left,top))
        else:
            d.rectangle((left,top,left+w,top+h),fill='#203643')
            d.text((left+80,top+550),'MAP BACKGROUND UNAVAILABLE',font=font(65),fill=MUTED)
        for n,r in enumerate(rows):
            if basemap and r['lat'] is not None:
                px,py=basemap.point(r['lat'],r['lon']);x=left+px*w/3840;y=top+py*h/2160
                if left+25<x<left+w-25 and top+25<y<top+h-25:
                    color='#f4ca71' if n//3==page else '#e7dcca'
                    d.ellipse((x-30,y-30,x+30,y+30),fill=color,outline='#17232c',width=4)
                    label=str(n+1);d.text((x-d.textlength(label,font=font(38))/2,y-25),label,font=font(38),fill='#17232c')
        for i,r in enumerate(rows[page*3:page*3+3]):
            x,y=2410,630+i*400
            d.rounded_rectangle((x,y,3648,y+365),radius=16,fill='#203643')
            title=" / ".join(part for part in (f"{page*3+i+1:02d}","PLANNED" if r["planned"] else "",customer_text(r).upper()) if part)
            d.text((x+28,y+16),title,font=fit(d,title,52,1170),fill='#90d5e1' if r['planned'] else '#f4ca71')
            lines=wrap(r['location'],51,1170)
            if len(lines)>2:lines[1]=shorten(lines[1]+' ...',51,1170)
            for j,line in enumerate(lines[:2]):d.text((x+28,y+88+j*60),line,font=font(51,False),fill=PAPER)
            timing=(planned_window(r) if r['planned'] else 'EST. RESTORE '+restoration(r,data['minute']*60))
            d.text((x+28,y+222),timing,font=fit(d,timing,42,1170,False),fill=PAPER)
            detail=shorten(r.get('provider','Newfoundland Power')+' / '+r['cause']+(' / LAST KNOWN' if not r.get('fresh',True) else ''),38,1170)
            d.text((x+28,y+290),detail,font=fit(d,detail,39,1170,False),fill=MUTED)
        d.text((left+18,top+h-56),'APPROXIMATE LOCATIONS / © OpenStreetMap contributors',font=font(29),fill='#17232c',stroke_width=2,stroke_fill='#f4f0e7')
    footer='RESTORATION TIMES ARE ESTIMATES / NEWFOUNDLANDPOWER.COM + MY.NLHYDRO.COM'
    d.text((192,1870),footer,font=fit(d,footer,32,3456,False),fill=MUTED)
    if pages>1:d.text((3300,520),f'PAGE {page+1}/{pages}',font=font(36),fill='#f4ca71')
    return im
