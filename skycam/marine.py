"""ECCC East Coast marine XML, bounded retrieval and dated native cards."""
from .public_errors import public_error
import asyncio,json,re,threading,time
from datetime import datetime,timezone
import httpx
from .alert_verification import safe_xml
from .storage import save_json

BASE='https://dd.weather.gc.ca/today/marine_weather/atlantic/'
SITE='m0000062'
SOURCE='https://eccc-msc.github.io/open-data/msc-data/marine-weather/readme_marine-weather-datamart_en/'

def issued(node):
    if node is None:return None
    value=node.findtext("dateTime[@zone='UTC']/timeStamp",'')
    try:return datetime.strptime(value,'%Y%m%d%H%M').replace(tzinfo=timezone.utc).timestamp()
    except ValueError:return None

def parse(raw):
    if len(raw)>2_000_000:raise ValueError('Marine XML exceeds size limit')
    root=safe_xml(raw)
    if root.tag!='marineData' or root.findtext('area')!='East Coast':raise ValueError('Unexpected marine forecast area')
    regular=root.find('regularForecast');waves=root.find('waveForecast')
    wind_time=issued(regular);wave_time=issued(waves)
    if wind_time is None:raise ValueError('Marine forecast issue time missing')
    groups=[]
    for loc in regular.findall('location')[:8]:
        name=loc.get('name','East Coast');w=loc.find('weatherCondition')
        if w is None:continue
        fields={tag:(w.findtext(tag) or '').strip() for tag in ('wind','weatherVisibility','airTemperature','freezingSpray')}
        if not fields['wind']:continue
        warn=[]
        for wl in root.findall('warnings/location'):
            if wl.get('name') not in (name,'East Coast'):continue
            for event in wl.findall('event'):
                if event.get('status')=='IN EFFECT':warn.append(event.get('name','Marine warning'))
        wave=None
        if waves is not None:
            for wl in waves.findall('location'):
                if wl.get('name') not in (name,'East Coast'):continue
                wave={'issued_at':wave_time,'period':wl.findtext('weatherCondition/periodOfCoverage',''),
                      'text':wl.findtext('weatherCondition/textSummary','')}
        groups.append({'name':name,'issued_at':wind_time,'period':w.findtext('periodOfCoverage',''),
                       'fields':fields,'warnings':warn,'waves':wave})
    if not groups:raise ValueError('No dated wind forecasts in marine XML')
    return {'groups':groups,'created_at':issued(root)}

class Marine:
    def __init__(self,data):
        self.path=data/'broadcast/marine-cache.json';self.lock=threading.RLock();self.data={};self.error=None
        try:self.data=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
    async def refresh(self):
        async with httpx.AsyncClient(timeout=12,follow_redirects=False,trust_env=False) as c:
            async def get(url):
                out=bytearray()
                async with c.stream('GET',url) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        out.extend(chunk)
                        if len(out)>2_000_000:raise ValueError('Marine source exceeds size limit')
                return bytes(out)
            listing=(await get(BASE)).decode('utf-8')
            hours=sorted(set(re.findall(r'href="([0-2][0-9])/"',listing)),reverse=True)[:12]
            for hour in hours:
                url=BASE+hour+'/'
                listing=(await get(url)).decode('utf-8')
                names=re.findall(r'href="(\d{8}T\d{6}\.\d{3}Z_MSC_MarineWeather_'+SITE+r'_en\.xml)"',listing)
                if not names:continue
                source=url+max(names)
                with self.lock:old=dict(self.data)
                parsed={k:v for k,v in old.items() if k not in ('checked_at','source_url')} if old.get('source_url')==source else parse(await get(source))
                if not parsed.get('groups'):raise ValueError('Empty marine forecast')
                for group in parsed['groups']:
                    if group['issued_at']>time.time()+300:raise ValueError('Marine issue time is in the future')
                parsed.update(source_url=source,checked_at=time.time())
                with self.lock:self.data=parsed;self.error=None;save_json(self.path,parsed)
                return
            raise ValueError('No current East Coast marine XML found')
    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            d=self.data;groups=[];checked=d.get('checked_at',0)
            try:
                for group in d.get('groups',[]):
                    if not 0<=now-group['issued_at']<=18*3600:continue
                    g={**group};w=g.get('waves')
                    if w and (w.get('issued_at') is None or not 0<=now-w['issued_at']<=24*3600):g['waves']=None
                    groups.append(g)
                available=bool(groups) and 0<=now-checked<5400
            except (KeyError,TypeError,ValueError):available=False;groups=[]
            return {'available':available,'groups':groups if available else [],'checked_at':checked,
                    'cached':bool(self.error) or now-checked>1200,'error':self.error,
                    'source_url':d.get('source_url',SOURCE),'source':'Environment and Climate Change Canada'}
    async def watch(self):
        while True:
            try:await self.refresh()
            except Exception as exc:
                with self.lock:self.error=public_error(exc)[:180]
            await asyncio.sleep(600)

def pages(data):
    from .alert_graphics import wrap,local
    result=[]
    for g in data.get('groups',[]):
        lines=[]
        for key,label in [('wind','Wind'),('weatherVisibility','Weather and visibility'),('airTemperature','Air temperature'),('freezingSpray','Freezing spray')]:
            if g['fields'].get(key):lines+=wrap(('' if key=='wind' else label+': ')+g['fields'][key],72,3300)
        for i in range(0,len(lines),8):result.append({'group':g,'title':'WIND & WEATHER','issued_at':g['issued_at'],'period':g['period'],'lines':lines[i:i+8]})
        w=g.get('waves')
        if w and w['text']:
            lines=wrap(w['text'],72,3300)
            for i in range(0,len(lines),7):result.append({'group':g,'title':'SEAS','issued_at':w['issued_at'],'period':w['period'],'lines':lines[i:i+7]})
    return result

def image(data,page):
    from .community_cards import heading,MUTED
    from .graphics import font,fit,PAPER
    from .alert_graphics import local
    rows=pages(data)
    im,d=heading('COASTAL MARINE FORECAST','EAST COAST OF NEWFOUNDLAND / ECCC')
    if not rows:
        d.text((240,850),'MARINE FORECAST UNAVAILABLE',font=font(116),fill=PAPER)
        d.text((240,1050),'weather.gc.ca/marine',font=font(56,False),fill=MUTED)
        return im
    row=rows[page%len(rows)];g=row['group'];name=g['name'].upper()
    d.text((192,615),name,font=fit(d,name,90,3456),fill=PAPER)
    d.text((192,740),row['title']+' / ISSUED '+local(row['issued_at'])+' NL',font=font(44),fill='#ffb578')
    d.text((192,830),row['period'],font=font(58),fill=MUTED)
    for i,line in enumerate(row['lines']):d.text((192,940+i*88),line,font=font(72,False),fill=PAPER)
    warning=' / '.join(g['warnings']) or 'Refer to ECCC for current warnings and updates'
    d.text((192,1700),warning.upper(),font=fit(d,warning.upper(),54,3456),fill='#ffb578')
    d.text((192,1800),'SOURCE: ENVIRONMENT AND CLIMATE CHANGE CANADA / '+('CACHED FORECAST' if data['cached'] else ''),font=font(34,False),fill=MUTED)
    if len(rows)>1:d.text((3290,1860),f'{page%len(rows)+1} / {len(rows)}',font=font(44),fill=PAPER)
    return im
