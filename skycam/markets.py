"""Attributed daily reference figures. Never labelled real-time trading quotes."""
from .bounded_http import bounded_get
from .public_errors import public_error
import asyncio,json,math,re,threading,time
from datetime import date,datetime,timedelta,timezone
from html.parser import HTMLParser
import httpx
from .storage import save_json
from .live_markets import LiveMarkets,SYMBOLS,METALS,STOCKS
from .tmx_markets import TmxMarkets

SOURCES={'fx':'https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=10','wti':'https://www.eia.gov/dnav/pet/hist/RWTCd.htm','brent':'https://www.eia.gov/dnav/pet/hist/RBRTED.htm'}
class OilTable(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=[];self.cell=None;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag=='td':self.cell=dict(attrs).get('class');self.parts=[]
    def handle_data(self,data):
        if self.cell in ('B6','B3'):self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='td':
            if self.cell in ('B6','B3'):self.row.append((self.cell,''.join(self.parts).strip()))
            self.cell=None
        if tag=='tr' and self.row and self.row[0][0]=='B6':self.rows.append(self.row)

def oil_rows(text):
    parser=OilTable();parser.feed(text);result=[]
    for row in parser.rows:
        match=re.match(r'(\d{4})\s+([A-Za-z]{3})-\s*(\d{1,2})\s+to',row[0][1])
        if not match:continue
        start=datetime.strptime(' '.join(match.groups()),'%Y %b %d').date()
        values=[v for cls,v in row[1:] if cls=='B3']
        if len(values)!=5:continue
        for offset,value in enumerate(values):
            try:price=float(value)
            except ValueError:continue
            if math.isfinite(price) and -1000<price<10000:result.append({'date':(start+timedelta(days=offset)).isoformat(),'value':price})
    if not result:raise ValueError('No dated oil observations in source table')
    return sorted(result,key=lambda r:r['date'])[-10:]

def fx_rows(data):
    result=[]
    for row in data['observations']:
        try:
            day=date.fromisoformat(row['d']);value=float(row['FXUSDCAD']['v'])
            if math.isfinite(value) and .01<value<100:result.append({'date':day.isoformat(),'value':value})
        except (ValueError,TypeError,KeyError):continue
    if not result:raise ValueError('No dated exchange-rate observations')
    return sorted(result,key=lambda r:r['date'])[-10:]

class Markets:
    def __init__(self,data):
        self.live=LiveMarkets(cache_path=data/'broadcast'/'stock-quotes-cache.json')
        self.tmx=TmxMarkets(data)
        self.path=data/'broadcast'/'markets-cache.json';self.lock=threading.RLock();self.values={};self.errors={}
        try:
            if self.path.exists():
                loaded=json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(loaded,dict):self.values=loaded
        except (OSError,ValueError):pass
    async def refresh(self):
        async with httpx.AsyncClient(timeout=15,follow_redirects=True,trust_env=False) as client:
            for key,url in SOURCES.items():
                try:
                    response=await bounded_get(client,url);response.raise_for_status()
                    if len(response.content)>2_000_000:raise ValueError('Source response exceeds limit')
                    rows=fx_rows(response.json()) if key=='fx' else oil_rows(response.text)
                    with self.lock:self.values[key]={'rows':rows,'checked_at':time.time()};self.errors.pop(key,None)
                except Exception as exc:
                    with self.lock:self.errors[key]=public_error(exc)[:160]
        with self.lock:save_json(self.path,self.values)
    def public(self,now=None):
        now=time.time() if now is None else now;today=datetime.fromtimestamp(now,timezone.utc).date();cards=[]
        with self.lock:
            for key,label,source in [('fx','CAD / USD','BANK OF CANADA'),('wti','WTI / CUSHING','U.S. EIA'),('brent','BRENT / EUROPE','U.S. EIA')]:
                cached=self.values.get(key,{})
                if not isinstance(cached,dict):cached={}
                checked=cached.get('checked_at',0)
                if not isinstance(checked,(float,int)) or not math.isfinite(checked):checked=0
                try:
                    rows=sorted([r for r in cached.get('rows',[]) if isinstance(r,dict) and date.fromisoformat(r['date'])<=today and isinstance(r['value'],(float,int)) and math.isfinite(r['value']) and (.01<r['value']<100 if key=='fx' else -1000<r['value']<10000)],key=lambda r:r['date'])
                    last=rows[-1];previous=rows[-2] if len(rows)>1 else None
                    old=(today-date.fromisoformat(last['date'])).days>10
                    available=not old and 0<=now-checked<7*86400
                    value=1/last['value'] if key=='fx' else last['value']
                    prev=(1/previous['value'] if key=='fx' else previous['value']) if previous else None
                    if not math.isfinite(value):raise ValueError('Nonfinite price')
                except (KeyError,ValueError,TypeError,IndexError,ZeroDivisionError):available=False;last={};value=prev=None
                history=[{'at':datetime.fromisoformat(r['date']).replace(tzinfo=timezone.utc).timestamp(),
                          'value':1/r['value'] if key=='fx' else r['value'],'date':r['date']} for r in rows[-10:]] if available else []
                cards.append({'id':key,'label':label,'source':source,'url':SOURCES[key],'available':available,'value':value if available else None,'change':value-prev if available and prev is not None else None,'date':last.get('date'),'checked_at':checked,'cached':key in self.errors or now-checked>3600,'error':self.errors.get(key),'unit':'USD FOR 1 CAD' if key=='fx' else 'USD PER BARREL',
                    'history':history,'history_kind':'DAILY OBSERVATIONS','change_basis':'PREVIOUS DAILY OBSERVATION',
                    'previous_date':previous['date'] if available and previous else None,
                    'change_percent':(value-prev)/abs(prev)*100 if available and prev else None})
        live=self.live.public(now)
        for i,row in enumerate(cards):
            current=live['quotes'].get(row['id'])
            if current and current['available']:
                cards[i]={**row,**current,'date':datetime.fromtimestamp(current['observed_at'],timezone.utc).isoformat(),
                          'error':None,'daily_reference':False}
            else:
                row['daily_reference']=True
                row['quote_kind']='DAILY REFERENCE'
                row['live_unavailable']=live['configured']
        for symbol,(key,label,unit) in SYMBOLS.items():
            if key not in (*METALS,*STOCKS):continue
            current=live['quotes'].get(key)
            if current and current['available']:
                cards.append({**current,'daily_reference':False})
            else:
                cards.append({'id':key,'label':label,'unit':unit,'symbol':symbol,'available':False,
                    'value':None,'change':None,'history':[],'daily_reference':False,'cached':False,
                    'source':'FINNHUB' if key in STOCKS else 'FINNHUB / OANDA',
                    'quote_kind':'STOCK PROVIDER UPDATE' if key in STOCKS else 'CFD PROVIDER UPDATE',
                    'observed_at':None,'age_seconds':0,'error':'No fresh provider observation'})
        tsx=self.tmx.public(now)
        if tsx['enabled']:cards.append(tsx)
        return {'pages':[['tsx','fx','wti','brent'] if tsx['enabled'] else ['fx','wti','brent'],list(METALS),list(STOCKS)],'cards':cards,'live':live,'tmx':tsx,'description':'Provider updates and dated daily references; TMX quote time and delay are unverified'}
    async def watch(self):
        await asyncio.gather(self.watch_daily(),self.live.watch(),self.tmx.watch())
    async def watch_daily(self):
        while True:
            try:await self.refresh()
            except Exception as exc:self.errors['cache']=public_error(exc)[:160]
            await asyncio.sleep(1800)
