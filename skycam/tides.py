"""CHS high/low predictions for the licensed station display, never observations."""
from .bounded_http import bounded_get
from .public_errors import public_error
import asyncio,json,math,threading,time
from datetime import datetime,timedelta,timezone
import httpx
from .storage import save_json
from .daylight import TZ
STATION='5cebf1e33d0f4a073c4bc176'
URL='https://api-iwls.dfo-mpo.gc.ca/api/v1/stations/'+STATION+'/data'
SOURCE='https://tides.gc.ca/en/stations/00905'

def parse(rows):
    if not isinstance(rows,list):raise ValueError('Expected a prediction list')
    result={}
    for r in rows:
        try:
            at=datetime.fromisoformat(r['eventDate'].replace('Z','+00:00'));value=float(r['value'])
            if at.tzinfo and str(r.get('qcFlagCode'))=='1' and math.isfinite(value) and -10<value<20:result[at.timestamp()]={'at':at.isoformat(),'value':value}
        except (ValueError,TypeError,KeyError,AttributeError):continue
    ordered=[result[k] for k in sorted(result)]
    events=[]
    # Each interior extremum must agree with both neighbours; endpoints are not guessed.
    for a,b,c in zip(ordered,ordered[1:],ordered[2:]):
        gaps=[(datetime.fromisoformat(y['at'])-datetime.fromisoformat(x['at'])).total_seconds() for x,y in ((a,b),(b,c))]
        if not all(3600<g<43200 for g in gaps):continue
        kind='HIGH' if b['value']>max(a['value'],c['value']) else 'LOW' if b['value']<min(a['value'],c['value']) else None
        if kind:events.append({**b,'kind':kind})
    if not events:raise ValueError('No validated high/low predictions')
    return events

class Tides:
    def __init__(self,data):
        self.path=data/'broadcast'/'tides-cache.json';self.lock=threading.RLock();self.events=[];self.checked_at=0;self.error=None
        try:
            row=json.loads(self.path.read_text());checked=float(row['checked_at'])
            # Re-run validation against raw feed after a restart.
            events=parse(row['raw'])
            if math.isfinite(checked):self.events=events;self.checked_at=checked
        except (OSError,ValueError,TypeError,KeyError):pass
    async def refresh(self):
        now=datetime.now(timezone.utc);params={'time-series-code':'wlp-hilo','from':(now-timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),'to':(now+timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ')}
        async with httpx.AsyncClient(timeout=20,trust_env=False) as client:
            response=await bounded_get(client,URL,params=params);response.raise_for_status()
            if len(response.content)>250000:raise ValueError('Prediction response too large')
            raw=response.json();events=parse(raw)
        checked=time.time()
        with self.lock:
            save_json(self.path,{'raw':raw,'checked_at':checked});self.events=events;self.checked_at=checked;self.error=None
    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            fresh=0<=now-self.checked_at<48*3600
            events=[e for e in self.events if now<=datetime.fromisoformat(e['at']).timestamp()<=now+48*3600][:4] if fresh else []
            return {'station':'ST. JOHN\'S HARBOUR','station_code':'00905','events':events,'available':bool(events),'checked_at':self.checked_at,'cached':bool(self.error) or now-self.checked_at>7200,'error':self.error,'source':SOURCE,'description':'Predicted high and low tides, not measured water levels'}
    async def watch(self):
        while True:
            try:await self.refresh()
            except Exception as exc:self.error=public_error(exc)[:160]
            await asyncio.sleep(3600)

def image(data):
    from .community_cards import heading,MUTED
    from .graphics import font,fit,PAPER
    from PIL import ImageDraw
    im,d=heading('HARBOUR TIDES',"ST. JOHN'S / CHS STATION 00905 / PREDICTED HIGH & LOW WATER")
    events=data['events']
    if not events:
        d.text((240,900),'TIDE PREDICTIONS UNAVAILABLE',font=font(110),fill=PAPER)
    for i,event in enumerate(events):
        x=192+(i%2)*1760;y=640+(i//2)*480;at=datetime.fromisoformat(event['at']).astimezone(TZ)
        d.rounded_rectangle((x,y,x+1696,y+420),radius=22,fill='#203643')
        d.text((x+48,y+36),event['kind']+' TIDE',font=font(66),fill='#ffb578')
        d.text((x+48,y+127),at.strftime('%I:%M %p').lstrip('0'),font=font(150),fill=PAPER)
        d.text((x+48,y+326),at.strftime('%a, %b %d / %Z').upper(),font=font(42,False),fill=MUTED)
        d.text((x+1160,y+150),f"{event['value']:.2f} m",font=font(98),fill=PAPER)
    d.text((192,1700),'PREDICTED / METRES ABOVE CHART DATUM',font=font(38,False),fill=MUTED)
    stamp=datetime.fromtimestamp(data['checked_at'],TZ).strftime('%b %d, %I:%M %p %Z').upper() if data['checked_at'] else 'AWAITING SOURCE'
    d.text((192,1840),'CANADIAN HYDROGRAPHIC SERVICE / TIDES.GC.CA / NOT FOR NAVIGATION',font=font(36),fill='#ffb578')
    return im
