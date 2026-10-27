"""Timestamped official St. John's observations and forecasts, with explicit gaps."""
from .bounded_http import bounded_get_sync
from .public_errors import public_error
import asyncio,json,math,threading,time
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import httpx
from .map_theme import TIMEZONE,solar_events

SOURCE_URL='https://api.weather.gc.ca/collections/citypageweather-realtime/items/nl-24?f=json'
SOURCE_NAME='Environment and Climate Change Canada'

def english(value):
    return value.get('en') if isinstance(value,dict) else value
def numeric(field):
    if not isinstance(field,dict):return None
    value=english(field.get('value'))
    qa=english(field.get('qaValue'))
    if qa is not None and qa!=100:return None
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None
def timestamp(value):
    try:
        value=english(value);dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.timestamp() if dt.tzinfo else None
    except (AttributeError,TypeError,ValueError):return None
def parse_weather(raw):
    if raw.get('id')!='nl-24':raise ValueError('Unexpected weather location')
    p=raw['properties'];current=p.get('currentConditions') or {};group=p.get('forecastGroup') or {}
    wind=current.get('wind') or {};forecasts=[]
    for entry in (group.get('forecasts') or [])[:3]:
        temperatures=(entry.get('temperatures') or {}).get('temperature') or []
        temperatures=[{'kind':english(t.get('class')),'value':numeric(t)} for t in temperatures if numeric(t) is not None]
        forecasts.append({'period':english((entry.get('period') or {}).get('textForecastName')) or 'Forecast',
            'summary':english((entry.get('abbreviatedForecast') or {}).get('textSummary')) or english(entry.get('cloudPrecip')) or 'Details unavailable',
            'details':english(entry.get('textSummary')),'temperatures':temperatures})
    return {'location':english(p.get('name')) or "St. John's",'station':english((current.get('station') or {}).get('value')) or 'Station not reported',
        'observed_at':timestamp(current.get('timestamp')),'forecast_at':timestamp(group.get('timestamp')),
        'condition':english(current.get('condition')) or 'Condition not reported',
        'temperature_c':numeric(current.get('temperature')),'humidity_pct':numeric(current.get('relativeHumidity')),
        'pressure_kpa':numeric(current.get('pressure')),'visibility_km':numeric(current.get('visibility')),
        'wind_kmh':numeric(wind.get('speed')),'gust_kmh':numeric(wind.get('gust')),
        'wind_direction':english((wind.get('direction') or {}).get('value')),'forecasts':forecasts,
        'source':SOURCE_NAME,'source_url':SOURCE_URL}

class Weather:
    def __init__(self,data):
        self.path=data/'weather/official.json';self.lock=threading.RLock();self.data=None;self.fetched_at=0;self.error=None
        if self.path.exists():
            try:
                cache=json.loads(self.path.read_text(encoding='utf-8'));self.data=parse_weather(cache['raw']);self.fetched_at=float(cache['fetched_at'])
            except (ValueError,KeyError,TypeError,OSError):self.error='Saved weather could not be read'
    def fetch(self):
        try:
            with httpx.Client(timeout=12,follow_redirects=True) as client:
                r=bounded_get_sync(client,SOURCE_URL,headers={'User-Agent':'SkyCam247 local weather display','Accept':'application/geo+json'});r.raise_for_status()
                if len(r.content)>2_000_000:raise ValueError('Weather reply is unexpectedly large')
                raw=r.json();parsed=parse_weather(raw)
            now=time.time();self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps({'fetched_at':now,'raw':raw}),encoding='utf-8');tmp.replace(self.path)
            with self.lock:self.data=parsed;self.fetched_at=now;self.error=None
        except Exception as exc:
            with self.lock:self.error=public_error(exc)[:160]
    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            data=dict(self.data or {});fetched=self.fetched_at;error=self.error
        observation_age=now-data['observed_at'] if data.get('observed_at') else None
        forecast_age=now-data['forecast_at'] if data.get('forecast_at') else None
        current_ok=observation_age is not None and -300<=observation_age<=7200 and 0<=now-fetched<=3600
        forecast_ok=forecast_age is not None and -300<=forecast_age<=43200 and 0<=now-fetched<=3600
        if not current_ok:
            for key in ['temperature_c','humidity_pct','pressure_kpa','visibility_km','wind_kmh','gust_kmh','wind_direction']:data[key]=None
            data['condition']='Observation unavailable'
        if not forecast_ok:data['forecasts']=[]
        local=datetime.fromtimestamp(now,timezone.utc).astimezone(ZoneInfo(TIMEZONE));rise,setting=solar_events(local.date())
        return {**data,'current_available':current_ok,'forecast_available':forecast_ok,'fetched_at':fetched,'fetch_error':error,
            'cached':bool(error or now-fetched>900),'sunrise':rise.isoformat(),'sunset':setting.isoformat(),
            'solar_date':local.date().isoformat(),'source':SOURCE_NAME,'source_url':SOURCE_URL}
    async def watch(self):
        while True:
            await asyncio.to_thread(self.fetch);await asyncio.sleep(300)
