"""Bounded Newfoundland and Labrador 511 travel adapter."""
import asyncio,json,re,threading,time
from pathlib import Path
import httpx
from .bounded_http import bounded_get
from .public_errors import public_error
from .station_config import secret

BASE='https://511nl.ca/api'
ENDPOINTS={
    'roads':'v3/get/winterroads',
    'events':'v2/get/event',
    'ferries':'v2/get/ferryterminals',
    'winds':'v2/get/windwarnings',
    'advisories':'v2/get/alerts',
}
SOURCE='Newfoundland and Labrador 511'
SOURCE_URL='https://511nl.ca/'


def clean(value,limit=260):
    text=re.sub(r'\s+',' ',str(value or '')).strip()
    return ''.join(c for c in text if c>=' ' and c!='\x7f')[:limit]


def rows(value,name):
    if not isinstance(value,list) or len(value)>5000:raise ValueError(f'Invalid {name} reply')
    if any(not isinstance(row,dict) for row in value):raise ValueError(f'Invalid {name} record')
    return value


def parse(payload,now):
    roads=[]
    for row in rows(payload.get('roads'),'road'):
        primary=clean(row.get('Primary Condition') or row.get('PrimaryCondition') or 'No report',80)
        if primary.casefold() in ('no report','bare','bare and dry','good'):continue
        roads.append({'road':clean(row.get('RoadwayName'),60),'location':clean(row.get('LocationDescription'),180),
                      'condition':primary,'visibility':clean(row.get('Visibility'),40),'updated_at':row.get('LastUpdated')})
    events=[]
    for row in rows(payload.get('events'),'event'):
        end=row.get('PlannedEndDate')
        if isinstance(end,(int,float)) and end and end<now-3600:continue
        events.append({'road':clean(row.get('RoadwayName'),60),'description':clean(row.get('Description'),300),
                       'type':clean(row.get('EventType'),40),'severity':clean(row.get('Severity'),30),
                       'closure':row.get('IsFullClosure') is True,'updated_at':row.get('LastUpdated')})
    ferries=[]
    for row in rows(payload.get('ferries'),'ferry'):
        status=clean(row.get('Status'),80)
        if status.casefold() in ('in service on schedule','no information available',''):continue
        ferries.append({'service':clean(row.get('ServiceName') or row.get('PortName'),120),
                        'status':status,'details':clean(row.get('Details'),240),'updated_at':row.get('LastUpdated')})
    winds=[]
    for row in rows(payload.get('winds'),'wind warning'):
        advisory=clean(row.get('Advisory'),100)
        if not advisory or advisory.casefold() in ('no wind advisory','none'):continue
        winds.append({'road':clean(row.get('RoadwayName'),60),'location':clean(row.get('Location'),160),
                      'advisory':advisory,'description':clean(row.get('Description'),260),'updated_at':row.get('LastUpdated')})
    advisories=[]
    for row in rows(payload.get('advisories'),'advisory'):
        end=row.get('EndTime')
        if isinstance(end,(int,float)) and end and end<now:continue
        advisories.append({'message':clean(row.get('Message'),260),'notes':clean(row.get('Notes'),300),
                           'important':row.get('HighImportance') is True,'updated_at':row.get('LastUpdated')})
    for group in (roads,events,ferries,winds,advisories):group.sort(key=lambda r:(not r.get('closure',False),not r.get('important',False),-(r.get('updated_at') or 0)))
    return {'roads':roads[:16],'events':events[:16],'ferries':ferries[:12],'winds':winds[:8],'advisories':advisories[:12]}


class Travel:
    def __init__(self,data,enabled=True):
        self.path=Path(data)/'travel/nl511.json';self.lock=threading.RLock()
        self.key=secret('nl511') if enabled else '';self.enabled=enabled
        self.data=None;self.checked_at=0;self.error=None
        if self.path.exists():
            try:
                saved=json.loads(self.path.read_text(encoding='utf-8'))
                self.data=saved['data'];self.checked_at=float(saved['checked_at'])
            except (OSError,ValueError,KeyError,TypeError):self.error='Saved travel data could not be read'

    async def refresh(self):
        if not self.key:return
        try:
            async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
                payload={}
                for name,endpoint in ENDPOINTS.items():
                    response=await bounded_get(client,f'{BASE}/{endpoint}',params={'key':self.key,'format':'json'},max_bytes=2_000_000,
                                               headers={'Accept':'application/json','User-Agent':'Broadcast station travel display'})
                    payload[name]=response.json()
            now=time.time();parsed=parse(payload,now)
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps({'checked_at':now,'data':parsed}),encoding='utf-8');temp.replace(self.path)
            with self.lock:self.data=parsed;self.checked_at=now;self.error=None
        except Exception as exc:
            with self.lock:self.error=public_error(exc)[:180]

    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:data=dict(self.data or {});checked=self.checked_at;error=self.error
        age=now-checked if checked else None;available=bool(data) and age is not None and 0<=age<=1800
        result={key:list(data.get(key,[])) if available else [] for key in ENDPOINTS}
        exceptional=any(result[key] for key in ENDPOINTS)
        count=sum(len(result[key]) for key in ENDPOINTS)
        return {**result,'configured':bool(self.key),'available':available,'exceptional':exceptional,
                'checked_at':checked or None,'cached':bool(error) or bool(age and age>600),'error':error,
                'summary':f'{count} travel item'+('s' if count!=1 else '')+' requiring attention' if exceptional else 'No exceptional travel items reported' if available else 'Travel data unavailable',
                'source':SOURCE,'source_url':SOURCE_URL}

    async def watch(self):
        while True:
            await self.refresh();await asyncio.sleep(300)
