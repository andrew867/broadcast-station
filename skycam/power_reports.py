"""PUB report archive, isolated parsing and provenance-preserving SQLite series."""
from .public_errors import public_error
import asyncio,hashlib,json,os,re,sqlite3,sys,tempfile,threading,time
from contextlib import closing
from datetime import datetime,timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote,quote
import httpx
from .power_system import TZ
from .power_report_parser import VERSION
BASE='http://www.pub.nf.ca/applications/IslandInterconnectedSystem/'
INDEX=BASE+'DemandStatusReports.php'
BACKFILL_DAYS=90
BATCH=16

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            href=dict(attrs).get('href','')
            if href:self.links.append(href)

def links(text,base):
    parser=Links();parser.feed(text);return [urljoin(base,u) for u in parser.links]

def report_date(url):
    parts=urlsplit(url)
    if parts.scheme not in ('http','https') or parts.hostname!='www.pub.nf.ca' or parts.port not in (None,80,443) or parts.query or parts.fragment or parts.username:raise ValueError('Not an allowed PUB report URL')
    m=re.fullmatch(r'/applications/IslandInterconnectedSystem/files/reports/(\d{4})/(\d{2})/(\d{4}-\d{2}-\d{2}) - NLH - Island Supply and Demand Report\.pdf',unquote(parts.path))
    if not m or m[3][:7]!=m[1]+'-'+m[2]:raise ValueError('Unrecognised report filename')
    return datetime.strptime(m[3],'%Y-%m-%d').date()

async def fetch(client,url,limit):
    async with client.stream('GET',url,follow_redirects=False) as r:
        r.raise_for_status();raw=bytearray()
        async for part in r.aiter_bytes():
            raw.extend(part)
            if len(raw)>limit:raise ValueError('PUB response exceeds limit')
        return bytes(raw)

async def isolated_parse(raw,date):
    # Parsing never occupies the playout thread; timeout kills malformed documents.
    with tempfile.TemporaryDirectory(prefix='pub-report-') as folder:
        path=Path(folder)/'report.pdf';path.write_bytes(raw)
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','skycam.power_report_parser',str(path),date,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try:
            out,err=await asyncio.wait_for(process.communicate(),30)
            if process.returncode:raise ValueError('PDF rejected: '+err.decode(errors='replace').splitlines()[-1][:180])
            if len(out)>1_000_000:raise ValueError('Parser output exceeds limit')
            return json.loads(out)
        finally:
            if process.returncode is None:process.kill();await process.wait()

class PowerReports:
    def __init__(self,data):
        self.path=Path(data)/'history'/'power.sqlite3';self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.running=False;self.checked_at=0;self.error=None;self.pending=0
        with closing(self.connect()) as db,db:
            db.executescript('''CREATE TABLE IF NOT EXISTS pub_reports(date TEXT PRIMARY KEY,url TEXT NOT NULL,sha TEXT NOT NULL,parser TEXT NOT NULL,payload TEXT NOT NULL,checked REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS pub_revisions(sha TEXT PRIMARY KEY,date TEXT NOT NULL,url TEXT NOT NULL,imported REAL NOT NULL,pdf BLOB NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pub_values(report_date TEXT,metric TEXT,day TEXT,value REAL,unit TEXT,kind TEXT,sha TEXT,PRIMARY KEY(report_date,metric,day));
            CREATE TABLE IF NOT EXISTS pub_curves(report_date TEXT,series TEXT,minute INTEGER,mw REAL,sha TEXT,PRIMARY KEY(report_date,series,minute));
            CREATE TABLE IF NOT EXISTS pub_attempts(url TEXT PRIMARY KEY,checked REAL,error TEXT);''')
        self._load()
    def connect(self):return sqlite3.connect(self.path,timeout=10)
    def _load(self):
        with closing(self.connect()) as db:
            self.latest=[dict(json.loads(p),url=u,sha256=s) for p,u,s in db.execute('SELECT payload,url,sha FROM pub_reports ORDER BY date DESC LIMIT 370')]
            self.failures=[{'url':u,'checked_at':t,'error':e} for u,t,e in db.execute('SELECT url,checked,error FROM pub_attempts WHERE error IS NOT NULL ORDER BY checked DESC LIMIT 20')]
            self.revisions=db.execute('SELECT count(*) FROM pub_revisions').fetchone()[0]
    def commit(self,raw,url,data,now):
        sha=hashlib.sha256(raw).hexdigest();date=data['report_date'];payload=json.dumps(data,separators=(',',':'))
        with self.lock,closing(self.connect()) as db,db:
            size=db.execute('SELECT coalesce(sum(length(pdf)),0) FROM pub_revisions').fetchone()[0]
            if size+len(raw)>250_000_000 and not db.execute('SELECT 1 FROM pub_revisions WHERE sha=?',(sha,)).fetchone():raise ValueError('Report archive reached 250 MB; operator review required')
            db.execute('INSERT OR IGNORE INTO pub_revisions VALUES(?,?,?,?,?,?)',(sha,date,url,now,raw,payload))
            db.execute('INSERT OR REPLACE INTO pub_reports VALUES(?,?,?,?,?,?)',(date,url,sha,VERSION,payload,now))
            db.execute('DELETE FROM pub_values WHERE report_date=?',(date,));db.execute('DELETE FROM pub_curves WHERE report_date=?',(date,))
            values=[(date,'daily-peak',data['actual_date'],data['peak_mw'],'MW','actual',sha),(date,'exports-at-peak',data['actual_date'],data['exports_at_peak_mw'],'MW','actual',sha),(date,'lil-energy',data['actual_date'],data['lil_energy_mwh'],'MWh','actual',sha)]
            values += [(date,k,date,v,'MW','outlook-0800',sha) for k,v in data['outlook'].items()]
            for row in data['forecast']:
                values += [(date,k,row['day'],row[k+'_mw'],'MW','forecast',sha) for k in ('forecast','adjusted')]
            db.executemany('INSERT INTO pub_values VALUES(?,?,?,?,?,?,?)',values)
            if data['chart']:
                db.executemany('INSERT INTO pub_curves VALUES(?,?,?,?,?)',[(date,k,p['minute'],p['mw'],sha) for k,points in data['chart']['series'].items() for p in points])
            db.execute('INSERT OR REPLACE INTO pub_attempts VALUES(?,?,NULL)',(url,now))
        with self.lock:self._load()
    def attempt(self,url,now,error=None):
        with self.lock,closing(self.connect()) as db,db:db.execute('INSERT OR REPLACE INTO pub_attempts VALUES(?,?,?)',(url,now,error))
        with self.lock:self._load()
    async def refresh(self):
        if self.running:return
        self.running=True;now=time.time();today=datetime.now(TZ).date();cutoff=today-timedelta(days=BACKFILL_DAYS)
        try:
            async with httpx.AsyncClient(timeout=25,trust_env=False) as client:
                index=(await fetch(client,INDEX,1_000_000)).decode('utf-8',errors='replace')
                months=sorted(set(u for u in links(index,INDEX) if re.fullmatch(re.escape(BASE)+r'\d{4}_\d{2}\.php',u)),reverse=True)
                months=[u for u in months if cutoff.strftime('%Y_%m')<=u.rsplit('/',1)[1][:7]<=today.strftime('%Y_%m')][:4]
                if not months:raise ValueError('No recent monthly report indexes found')
                urls={}
                for month in months:
                    body=(await fetch(client,month,1_000_000)).decode('utf-8',errors='replace')
                    for u in links(body,month):
                        try:d=report_date(u)
                        except ValueError:continue
                        if cutoff<=d<=today:urls[d.isoformat()]=quote(u,safe=':/%')
                if not urls:raise ValueError('No recent PDF reports found')
                with closing(self.connect()) as db:
                    checks={u:(t,e) for u,t,e in db.execute('SELECT url,checked,error FROM pub_attempts')}
                    existing={d:(s,v) for d,s,v in db.execute('SELECT date,sha,parser FROM pub_reports')}
                candidates=[]
                for date,url in sorted(urls.items(),reverse=True):
                    checked,error=checks.get(url,(0,None))
                    interval=86400
                    if now-checked>=interval or (date in existing and existing[date][1]!=VERSION):candidates.append((date,url))
                # Newest missing files first; revisits rotate through the older archive.
                candidates.sort(key=lambda pair:(pair[0] in existing,checks.get(pair[1],(0,None))[0],-int(pair[0].replace('-',''))))
                self.pending=len(candidates)
                for date,url in candidates[:BATCH]:
                    try:
                        raw=await fetch(client,url,4_000_000);sha=hashlib.sha256(raw).hexdigest()
                        if existing.get(date)==(sha,VERSION):self.attempt(url,now)
                        else:self.commit(raw,url,await isolated_parse(raw,date),now)
                    except Exception as exc:self.attempt(url,now,public_error(exc)[:240])
                    self.pending-=1
                    await asyncio.sleep(.2)
                self.checked_at=now;self.error=None
        except Exception as exc:self.error=public_error(exc)[:240]
        finally:self.running=False
    def public(self,report_date=None):
        with self.lock:
            latest=(next((r for r in self.latest if r['report_date']==report_date),None) if report_date else self.latest[0] if self.latest else None)
            trend=[{'day':r['actual_date'],'mw':r['peak_mw'],'peak_time':r['peak_time'],'report_date':r['report_date']} for r in reversed(self.latest)]
            return {'latest':latest,'trend':trend,'chart_count':sum(bool(r.get('chart')) for r in self.latest),'chart_rejections':[{'report_date':r['report_date'],'url':r['url'],'error':r['chart_error']} for r in self.latest if r.get('chart_error')],'count':len(self.latest),'revisions':self.revisions,'pending':self.pending,'importing':self.running,'checked_at':self.checked_at,'error':self.error,'failures':list(self.failures),'source':INDEX,'backfill_days':BACKFILL_DAYS}
    async def watch(self):
        await asyncio.sleep(15)
        while True:
            await self.refresh();await asyncio.sleep(900 if self.pending else 21600)

