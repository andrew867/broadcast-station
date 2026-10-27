"""YYT public flight-board facts with bounded polling and explicit cache age."""
from .public_errors import public_error
import asyncio, json, os, re, threading, time
from datetime import datetime, timedelta
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
import httpx
from .map_theme import TIMEZONE

TZ=ZoneInfo(TIMEZONE)
URLS={'arrivals':'https://stjohnsairport.com/arrtable.php?lang=en',
      'departures':'https://stjohnsairport.com/deptable.php?lang=en'}
FIELDS=('airline','flight-num','date','time','revised','city','status')
MONTHS={name:i+1 for i,name in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.row=None;self.field=None;self.text=[];self.recognized=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='table' and 'tblData' in a.get('class','').split():self.recognized=True
        if tag=='tr':self.row={}
        if tag=='td' and self.row is not None:
            self.field=next((f for f in FIELDS if f in a.get('class','').split()),None);self.text=[]
    def handle_data(self,data):
        if self.field:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='td' and self.field:
            self.row[self.field]=' '.join(' '.join(self.text).split());self.field=None
        if tag=='tr' and self.row is not None:
            if self.row:self.rows.append(self.row)
            self.row=None

def parse_table(html,now=None):
    now=datetime.now(TZ) if now is None else now.astimezone(TZ)
    parser=TableParser();parser.feed(html)
    if not parser.recognized or not parser.rows:raise ValueError('Airport table unavailable or changed')
    rows=[]
    for row in parser.rows:
        if any(f not in row for f in FIELDS):raise ValueError('Incomplete airport row')
        if any(len(v)>160 for v in row.values()):raise ValueError('Unexpectedly long airport value')
        if not re.fullmatch(r'[A-Z0-9 ]{2,16}',row['flight-num']):raise ValueError('Unrecognized flight number')
        match=re.fullmatch(r'(\d{1,2}) ([A-Za-z]{3})',row['date'])
        if not match or match[2] not in MONTHS:raise ValueError('Unrecognized airport date')
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',row['time']):raise ValueError('Unrecognized scheduled time')
        if row['revised'] and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',row['revised']):raise ValueError('Unrecognized revised time')
        hour,minute=map(int,row['time'].split(':'));candidates=[]
        for year in (now.year-1,now.year,now.year+1):
            try:candidates.append(datetime(year,MONTHS[match[2]],int(match[1]),hour,minute,tzinfo=TZ))
            except ValueError:pass
        if not candidates:raise ValueError('Invalid airport date')
        scheduled=min(candidates,key=lambda d:abs(d.timestamp()-now.timestamp()))
        if abs((scheduled.date()-now.date()).days)>3:raise ValueError('Airport schedule is out of date')
        rows.append({**row,'scheduled_at':scheduled.isoformat()})
    if len(rows)>250:raise ValueError('Airport table exceeds expected size')
    return rows

class Flights:
    def __init__(self,data):
        self.path=data/'flights'/'yyt.json';self.lock=threading.RLock();self.boards={}
        try:
            raw=json.loads(self.path.read_text(encoding='utf-8'))
            for direction,item in raw.items():
                if direction in URLS:
                    # Re-validate saved raw data using its original check date.
                    checked=float(item['checked_at']);rows=parse_table(item['html'],datetime.fromtimestamp(checked,TZ))
                    self.boards[direction]={'rows':rows,'checked_at':checked,'html':item['html'],'error':None}
        except (OSError,ValueError,KeyError,TypeError):pass
    def fetch(self):
        for direction,url in URLS.items():
            try:
                with httpx.Client(timeout=12,follow_redirects=True) as client:
                    with client.stream('GET',url,headers={'User-Agent':'SkyCam247 local YYT board','Cache-Control':'no-cache'}) as response:
                        response.raise_for_status();chunks=[];size=0
                        for chunk in response.iter_bytes():
                            size+=len(chunk)
                            if size>1_000_000:raise ValueError('Airport reply too large')
                            chunks.append(chunk)
                        html=b''.join(chunks).decode('utf-8-sig')
                rows=parse_table(html);checked=time.time()
                with self.lock:self.boards[direction]={'rows':rows,'checked_at':checked,'html':html,'error':None}
            except Exception as exc:
                with self.lock:
                    item=self.boards.setdefault(direction,{'rows':[],'checked_at':None})
                    item['error']=public_error(exc)[:160]
        with self.lock:cache={k:{'html':v['html'],'checked_at':v['checked_at']} for k,v in self.boards.items() if v.get('html')}
        if cache:
            self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp')
            with tmp.open('w',encoding='utf-8') as f:json.dump(cache,f);f.flush();os.fsync(f.fileno())
            tmp.replace(self.path)
    def public(self,direction,now=None):
        if direction not in URLS:raise ValueError('Unknown flight direction')
        now=time.time() if now is None else now
        with self.lock:item=dict(self.boards.get(direction,{}))
        checked=item.get('checked_at');age=now-checked if checked else None
        usable=age is not None and 0<=age<=1800
        # Keep recent completions/cancellations for context, then upcoming rows.
        rows=[r for r in item.get('rows',[]) if
              (now-3600<=datetime.fromisoformat(r['scheduled_at']).timestamp()<=now+86400 or
               (r['status'].lower() not in ('arrived','departed','cancelled','canceled') and
                now-86400<=datetime.fromisoformat(r['scheduled_at']).timestamp()<now-3600))] if usable else []
        rows=sorted(rows,key=lambda r:datetime.fromisoformat(r['scheduled_at']).timestamp())
        return {'direction':direction,'rows':rows,'available':usable,'cached':bool(usable and (item.get('error') or age>300)),
                'checked_at':checked,'error':item.get('error'),'timezone':TIMEZONE,
                'source':"St. John's International Airport",'source_url':'https://stjohnsairport.com/',
                'note':'Airport website status, not a guaranteed real-time feed. Confirm travel plans with your airline.'}
    async def watch(self):
        while True:
            try:await asyncio.to_thread(self.fetch)
            except Exception:pass  # Preserve the last timestamp; cache age still expires.
            await asyncio.sleep(120)
