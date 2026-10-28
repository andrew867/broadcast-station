"""Official Canadian geomagnetic forecast, used as optional sky context."""
import asyncio,json,re,threading,time
from html.parser import HTMLParser
from pathlib import Path
import httpx
from .bounded_http import bounded_get
from .public_errors import public_error

SOURCE='Natural Resources Canada, Canadian Space Weather Forecast Centre'
SOURCE_URL='https://spaceweather.gc.ca/forecast-prevision/short-court/zone-en.php'
LEVELS=('quiet','unsettled','active','stormy')


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):
        value=re.sub(r'\s+',' ',data).strip()
        if value:self.parts.append(value)


def parse(raw):
    parser=Text();parser.feed(raw)
    text=' | '.join(parser.parts)
    issued=re.search(r'(20\d\d-\d\d-\d\d).*?issued at\s+(\d\d?:\d\d)\s+UT',text,re.I)
    section=re.search(r'Current Conditions\s*\|\s*([^|]{1,80})\|\s*([^|]{1,80})\|\s*([^|]{1,80}).*?24 Hour Forecast\s*\|\s*([^|]{1,80})\|\s*([^|]{1,80})\|\s*([^|]{1,80})',text,re.I)
    if not section:raise ValueError('Geomagnetic table format changed')
    values=[re.sub(r'\s+',' ',value).strip().lower() for value in section.groups()]
    if any(not any(level in value for level in LEVELS) for value in values):raise ValueError('Unknown geomagnetic activity')
    return {'issued':(issued.group(1)+' '+issued.group(2)+' UTC') if issued else None,
            'current':dict(zip(('sub_auroral','auroral','polar'),values[:3])),
            'forecast_24h':dict(zip(('sub_auroral','auroral','polar'),values[3:]))}


class SpaceWeather:
    def __init__(self,data,enabled=True):
        self.path=Path(data)/'weather/space-weather.json';self.lock=threading.RLock()
        self.enabled=enabled;self.data=None;self.checked_at=0;self.error=None
        if self.path.exists():
            try:
                saved=json.loads(self.path.read_text(encoding='utf-8'));self.data=saved['data'];self.checked_at=float(saved['checked_at'])
            except (OSError,ValueError,KeyError,TypeError):self.error='Saved space-weather data could not be read'

    async def refresh(self):
        if not self.enabled:return
        try:
            async with httpx.AsyncClient(timeout=15,follow_redirects=True) as client:
                response=await bounded_get(client,SOURCE_URL,max_bytes=1_000_000,headers={'Accept':'text/html','User-Agent':'Broadcast station sky display'})
            parsed=parse(response.text);now=time.time()
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps({'checked_at':now,'data':parsed}),encoding='utf-8');temp.replace(self.path)
            with self.lock:self.data=parsed;self.checked_at=now;self.error=None
        except Exception as exc:
            with self.lock:self.error=public_error(exc)[:180]

    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:data=dict(self.data or {});checked=self.checked_at;error=self.error
        available=bool(data) and 0<=now-checked<=3600
        sub=(data.get('current') or {}).get('sub_auroral','') if available else ''
        return {**(data if available else {}),'available':available,'checked_at':checked or None,'cached':bool(error) or bool(checked and now-checked>1200),
                'error':error,'notable':any(level in sub for level in ('active','stormy')),
                'source':SOURCE,'source_url':SOURCE_URL}

    async def watch(self):
        while True:
            await self.refresh();await asyncio.sleep(900)
