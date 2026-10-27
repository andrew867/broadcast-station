"""NL Hydro public readings and bounded, timestamped local history."""
from .public_errors import public_error
import asyncio, math, re, sqlite3, threading, time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx

SOURCE='https://nlhydro.com/about-us/our-electricity-system/supply-and-demand/'
TZ=ZoneInfo('America/St_Johns')
METRICS={'island-demand':('Current Island System Demand','ISLAND DEMAND',15000),
 'muskrat-falls':('Current Muskrat Falls Generation','MUSKRAT FALLS',5000),
 'churchill-falls':('Current Churchill Falls Generation','CHURCHILL FALLS',15000)}
FRESH_SECONDS=1200
RETENTION_DAYS=90

class ReadingsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.depth=0;self.tag=None;self.text=[];self.row={}
    def handle_starttag(self,tag,attrs):
        if tag=='div':
            if self.depth:self.depth+=1
            elif 'sysgen' in dict(attrs).get('class','').split():self.depth=1;self.row={}
        if self.depth and tag in ('h3','button','strong'):self.tag=tag;self.text=[]
    def handle_data(self,data):
        if self.tag:self.text.append(data)
    def handle_endtag(self,tag):
        if tag==self.tag:
            if tag in self.row:raise ValueError('Repeated power field')
            self.row[tag]=' '.join(''.join(self.text).split());self.tag=None
        if tag=='div' and self.depth:
            self.depth-=1
            if not self.depth:self.rows.append(self.row);self.row={}

def local_stamp(value):
    naive=datetime.strptime(value,'%m/%d/%Y %I:%M %p')
    dt=naive.replace(tzinfo=TZ)
    if dt.utcoffset()!=naive.replace(tzinfo=TZ,fold=1).utcoffset():
        raise ValueError('Ambiguous utility local time during clock change')
    return dt.timestamp()

def parse_readings(text,now=None):
    now=time.time() if now is None else now
    if len(text)>1_000_000:raise ValueError('Power page exceeds size limit')
    parser=ReadingsParser();parser.feed(text);found={}
    for row in parser.rows:
        metric=next((k for k,v in METRICS.items() if row.get('h3')==v[0]),None)
        if metric is None:continue
        if metric in found:raise ValueError('Duplicate power reading')
        match=re.fullmatch(r'([\d,]+(?:\.\d+)?)\s+MW',row.get('button',''))
        if not match:raise ValueError('Power unit or value changed')
        mw=float(match.group(1).replace(',',''));observed=local_stamp(row.get('strong',''))
        if not 0<=mw<=METRICS[metric][2] or not now-31*86400<=observed<=now+300:raise ValueError('Power reading outside expected range')
        found[metric]={'metric':metric,'mw':mw,'observed_at':observed}
    if set(found)!=set(METRICS):raise ValueError('Power page is missing a named reading')
    return list(found.values())

class PowerSystem:
    def __init__(self,data):
        self.path=Path(data)/'history'/'power.sqlite3';self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.checked_at=0;self.error=None;self.verified=False;self.rows={};self.history={}
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS readings(metric TEXT NOT NULL, observed_at INTEGER NOT NULL, mw REAL NOT NULL, PRIMARY KEY(metric,observed_at)) WITHOUT ROWID')
        self._load(time.time())
    def connect(self):return sqlite3.connect(self.path,timeout=5)
    def _load(self,now):
        with self.connect() as db:
            self.rows={};self.history={}
            for key in METRICS:
                latest=db.execute('SELECT observed_at,mw FROM readings WHERE metric=? ORDER BY observed_at DESC LIMIT 1',(key,)).fetchone()
                if latest:self.rows[key]={'metric':key,'observed_at':latest[0],'mw':latest[1]}
                self.history[key]=[{'observed_at':r[0],'mw':r[1]} for r in db.execute('SELECT observed_at,mw FROM readings WHERE metric=? AND observed_at>=? ORDER BY observed_at DESC LIMIT 2000',(key,now-86400)).fetchall()][::-1]
    def record(self,rows,now):
        with self.lock:
            with self.connect() as db:
                db.executemany('INSERT INTO readings VALUES(?,?,?) ON CONFLICT(metric,observed_at) DO UPDATE SET mw=excluded.mw',[(r['metric'],int(r['observed_at']),r['mw']) for r in rows])
                db.execute('DELETE FROM readings WHERE observed_at<?',(now-RETENTION_DAYS*86400,))
            self._load(now);self.checked_at=now;self.error=None;self.verified=True
    async def refresh(self):
        try:
            async with httpx.AsyncClient(timeout=20,trust_env=False,follow_redirects=True) as client:
                async with client.stream('GET',SOURCE,headers={'Cache-Control':'no-cache'}) as response:
                    response.raise_for_status();raw=bytearray()
                    async for part in response.aiter_bytes():
                        raw.extend(part)
                        if len(raw)>1_000_000:raise ValueError('Power page exceeds size limit')
            now=time.time();rows=parse_readings(bytes(raw).decode('utf-8',errors='replace'),now)
            await asyncio.to_thread(self.record,rows,now)
        except Exception as exc:
            with self.lock:self.error=public_error(exc)[:180]
    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            rows=[]
            for metric,(_,label,_) in METRICS.items():
                row=dict(self.rows.get(metric,{'metric':metric,'mw':None,'observed_at':None}))
                row.update(label=label,history=[p for p in self.history.get(metric,[]) if p['observed_at']>=now-86400],
                    fresh=bool(self.verified and self.error is None and row['observed_at'] and -300<=now-row['observed_at']<FRESH_SECONDS and now-self.checked_at<FRESH_SECONDS))
                rows.append(row)
            return {'readings':rows,'checked_at':self.checked_at,'error':self.error,'source':SOURCE,'retention_days':RETENTION_DAYS,'minute':int(now//60)}
    async def watch(self):
        while True:
            await self.refresh();await asyncio.sleep(300)

def image(data):
    from .community_cards import heading,MUTED
    from .graphics import font,fit,PAPER
    im,d=heading('POWERING NEWFOUNDLAND & LABRADOR','NL HYDRO  /  DEMAND & GENERATION')
    now=data['minute']*60;colors=['#6dd6df','#f4bd75','#b2acff']
    notes=['Island customers, including system losses','Generation serving the island and other markets','Generation serving Labrador and export markets']
    for i,row in enumerate(data['readings']):
        x=192+i*1168;y=620;right=x+1120;color=colors[i]
        d.rounded_rectangle((x,y,right,1790),radius=18,fill='#203643')
        d.rectangle((x,y,right,y+8),fill=color)
        d.text((x+40,y+35),row['label'],font=fit(d,row['label'],66,1040),fill=PAPER)
        value=f"{row['mw']:,.0f}" if row['mw'] is not None else '--'
        d.text((x+40,y+135),value,font=font(190),fill=color)
        d.text((right-130,y+265),'MW',font=font(55),fill=PAPER)
        stamp=datetime.fromtimestamp(row['observed_at'],TZ).strftime('%b %d %I:%M %p %Z').replace(' 0',' ') if row['observed_at'] else 'NO READING YET'
        label=('AS OF ' if row['fresh'] else 'LAST REPORTED  ')+stamp
        d.text((x+40,y+375),label,font=fit(d,label,39,1040,False),fill=MUTED if row['fresh'] else '#f4bd75')
        points=row['history'];left=x+100;top=1185;bottom=1600;width=950
        d.text((x+40,1100),'PAST 24 HOURS',font=font(38),fill=MUTED)
        if points:
            lo=min(p['mw'] for p in points);hi=max(p['mw'] for p in points);pad=max(20,(hi-lo)*.15);lo=max(0,lo-pad);hi+=pad
            for val in (lo,(lo+hi)/2,hi):
                yy=bottom-(val-lo)/(hi-lo)*(bottom-top)
                d.line((left,yy,left+width,yy),fill='#3b5362',width=2)
                d.text((x+14,yy-19),str(round(val)),font=font(30),fill=MUTED)
            previous=None
            for point in points:
                xx=left+(point['observed_at']-(now-86400))/86400*width;yy=bottom-(point['mw']-lo)/(hi-lo)*(bottom-top)
                if previous and 0<point['observed_at']-previous[2]<=FRESH_SECONDS:d.line((previous[0],previous[1],xx,yy),fill=color,width=8)
                d.ellipse((xx-5,yy-5,xx+5,yy+5),fill=color);previous=(xx,yy,point['observed_at'])
            if len(points)<2:d.text((x+200,1375),'HISTORY STARTING',font=font(48),fill=MUTED)
        else:d.text((x+170,1375),'HISTORY NOT AVAILABLE',font=font(48),fill=MUTED)
        d.text((left,1620),'24H AGO',font=font(32),fill=MUTED);d.text((left+width-70,1620),'NOW',font=font(32),fill=MUTED)
        d.text((x+40,1715),notes[i],font=fit(d,notes[i],34,1040,False),fill=MUTED)
    d.text((192,1848),'DISTINCT SYSTEM MEASURES / VALUES ARE NOT ADDITIVE / SOURCE: NLHYDRO.COM',font=font(35,False),fill=MUTED)
    return im
