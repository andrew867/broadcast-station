"""Independent NAADS CAP receiver with authenticated, regional alert state.

Never imports playout, never takes a scene, never plays audio. Transport and
heartbeat repository behaviour follow the Pelmorex LMD guide. No OBPlayer code.
"""
from .public_errors import public_error
import asyncio,hashlib,json,re,threading,time
from collections import OrderedDict
from datetime import datetime
from urllib.parse import quote,urlsplit
import xml.etree.ElementTree as ET
import httpx
from .alert_verification import DssVerifier,safe_xml
from .alert_resources import resources
from .issuer_trust import policy_fingerprint
from .language_policy import english

HOSTS=('streaming1.naad-adna.pelmorex.com','streaming2.naad-adna.pelmorex.com')
REPOSITORIES=('capcp1.naad-adna.pelmorex.com','capcp2.naad-adna.pelmorex.com')
MAX_BYTES=5*1024*1024
NS={'c':'urn:oasis:names:tc:emergency:cap:1.2'}

def stamp(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.timestamp() if dt.tzinfo else None
    except (ValueError,AttributeError):return None

def refs(text):
    result=[]
    for part in text.split()[:100]:
        fields=part.split(',')
        if len(fields)==3 and stamp(fields[2]) is not None and all(0<len(f)<1024 for f in fields):result.append(tuple(fields))
    return result

def repository_path(reference):
    sender,identifier,sent=reference
    if stamp(sent) is None:raise ValueError('Invalid reference time')
    name=(sent+'I'+identifier).replace('-','_').replace('+','p').replace(':','_')
    return '/'+sent[:10]+'/'+quote(name,safe='_')+'.xml'

class Framer:
    def __init__(self):self.buffer=b''
    def feed(self,chunk):
        self.buffer+=chunk;messages=[]
        while True:
            end=re.search(br'</(?:[A-Za-z_][\w.-]*:)?alert\s*>',self.buffer)
            if end is None:break
            packet=self.buffer[:end.end()];self.buffer=self.buffer[end.end():]
            start=re.search(br'<(?:[A-Za-z_][\w.-]*:)?alert(?:\s|>)',packet)
            if start:
                declaration=packet.rfind(b'<?xml',0,start.start())
                packet=packet[declaration if declaration>=0 else start.start():]
                if len(packet)>MAX_BYTES:raise ValueError('CAP message exceeds size limit')
                messages.append(packet)
        if len(self.buffer)>MAX_BYTES:raise ValueError('CAP buffer exceeds size limit')
        return messages

class Alerts:
    def __init__(self,data,verifier=None,enabled=True):
        self.enabled=enabled
        self.path=data/'broadcast'/'weather-alerts.json';self.lock=threading.RLock()
        self.trust_fingerprint=policy_fingerprint()
        self.verifier=verifier or DssVerifier();self.verification_error=None;self.rejected=0;self.verified=0;self.retry_at={}
        self.items={};self.seen=OrderedDict();self.retired=OrderedDict();self.pending=OrderedDict()
        self.feeds={host:{'connected':False,'heartbeat_at':None,'received_at':None,'error':None} for host in HOSTS}
        self.dirty=False;self.recovery_error=None;self.recovered=0;self.running=False
        self.archive_pending=OrderedDict();self.archive_checked=None;self.archive_error=None
        self.archive_retry=0;self.archive_requested=False;self.disconnected_since={h:None for h in HOSTS}
        if self.enabled and self.path.exists():
            try:
                saved=json.loads(self.path.read_text(encoding='utf-8'));self.items=saved.get('items',{})
                self.retired=OrderedDict(saved.get('retired',[]));self.seen=OrderedDict(saved.get('seen',[]))
                if saved.get('schema')!=2 or saved.get('trust_fingerprint')!=self.trust_fingerprint:
                    for item in self.items.values():
                        reference=(item['sender'],item['identifier'],item['sent']);self.pending[self.key(reference)]=reference
                    self.items={};self.seen.clear();self.retired.clear();self.dirty=True
            except (ValueError,OSError):self.recovery_error='Saved alert cache could not be loaded'
    @staticmethod
    def key(reference):return json.dumps(reference,separators=(',',':'))
    def ingest(self,packet,host,now=None):
        if not self.enabled:return
        now=now or time.time()
        if len(packet)>MAX_BYTES or b'<!DOCTYPE' in packet.upper() or b'<!ENTITY' in packet.upper():raise ValueError('Unsupported CAP XML')
        root=safe_xml(packet)
        if root.tag!='{'+NS['c']+'}alert':raise ValueError('Expected CAP 1.2 alert')
        txt=lambda node,name:(node.findtext('c:'+name,default='',namespaces=NS) or '').strip()
        identity=(txt(root,'sender'),txt(root,'identifier'),txt(root,'sent'));key=self.key(identity)
        if not identity[0] or not identity[1] or stamp(identity[2]) is None:raise ValueError('Incomplete CAP identity')
        status=txt(root,'status');message_type=txt(root,'msgType');references=refs(txt(root,'references'))
        with self.lock:
            if host in self.feeds:self.feeds[host]['received_at']=now
            if status=='System' and identity[0]=='NAADS-Heartbeat':
                if host in self.feeds:self.feeds[host]['heartbeat_at']=now
                for reference in references:
                    rk=self.key(reference)
                    if rk not in self.seen and rk not in self.pending:self.pending[rk]=reference
                while len(self.pending)>100:self.pending.popitem(last=False)
                return
            if key in self.seen:return
            if status!='Actual' or txt(root,'scope')!='Public':return
            if stamp(identity[2])>now+300:raise ValueError('Alert sent time is in the future')
        # Network verification never holds the state lock or delays playout.
        try:
            verification=self.verifier(packet)
            if verification.get('verified') is not True:raise ValueError('Signature was not verified')
        except Exception as exc:
            with self.lock:
                self.verification_error=public_error(exc)[:300];self.rejected+=1
                self.pending[key]=identity;self.retry_at[key]=now+60
                while len(self.pending)>100:
                    old,_=self.pending.popitem(last=False);self.retry_at.pop(old,None)
            raise ValueError(self.verification_error) from exc
        with self.lock:
            if key in self.seen:return
            self.verified+=1;self.verification_error=None
            self.seen[key]=now;self.pending.pop(key,None);self.dirty=True
            while len(self.seen)>2000:self.seen.popitem(last=False)
            if status!='Actual' or txt(root,'scope')!='Public':return
            if message_type in ('Update','Cancel'):
                for reference in references:
                    # An unrelated sender may not retire another issuer's alert.
                    if reference[0]==identity[0]:
                        rk=self.key(reference);self.items.pop(rk,None);self.retired[rk]=now
            while len(self.retired)>2000:self.retired.popitem(last=False)
            if key in self.retired or message_type not in ('Alert','Update'):return
            blocks=[]
            info_nodes=root.findall('c:info',NS)
            minor_names=('none','text','correction','resource','layer','other')
            minor_update=message_type=='Update' and bool(references) and bool(info_nodes) and all(
                any(txt(p,'valueName')=='profile:CAP-CP:1.0:MinorChange' and txt(p,'value').lower() in minor_names
                    for p in info.findall('c:parameter',NS)) for info in info_nodes)
            for info in root.findall('c:info',NS):
                language=txt(info,'language') or 'en-US'
                if not language.lower().startswith(('en','fr')):continue
                categories=[n.text for n in info.findall('c:category',NS)]
                expires=stamp(txt(info,'expires'));effective=stamp(txt(info,'effective')) or stamp(identity[2])
                if expires is None or expires<=now:continue
                areas=[]
                for area in info.findall('c:area',NS):
                    label=txt(area,'areaDesc')
                    codes=[(txt(g,'valueName'),txt(g,'value')) for g in area.findall('c:geocode',NS)]
                    sgc=[v for n,v in codes if n.startswith('profile:CAP-CP:Location:')]
                    nl=any(re.fullmatch(r'10(?:\d{2}|\d{5})?',v) for v in sgc)
                    if not sgc:nl=bool(re.search(r'newfoundland|labrador|avalon',label,re.I))
                    if nl:areas.append(label[:1500])
                if not areas:continue
                parameters={txt(p,'valueName'):txt(p,'value') for p in info.findall('c:parameter',NS)}
                immediate=parameters.get('layer:SOREM:1.0:Broadcast_Immediately','').lower()=='yes'
                if 'Met' not in categories and not immediate:continue
                broadcast_text=parameters.get('layer:SOREM:1.0:Broadcast_Text','')
                blocks.append({'language':language,'categories':categories,'broadcast_text':broadcast_text,'event':txt(info,'event')[:300],'headline':txt(info,'headline')[:1000],'description':txt(info,'description')[:16000],'instruction':txt(info,'instruction')[:8000],'sender_name':txt(info,'senderName')[:300],'severity':txt(info,'severity'),'urgency':txt(info,'urgency'),'certainty':txt(info,'certainty'),'areas':areas,'expires':expires,'effective':effective,'broadcast_immediate':immediate,'minor_update':minor_update,'audio_resources':resources(info,NS)})
            if blocks:self.items[key]={'message_type':message_type,'references':references,'identifier':identity[1],'sender':identity[0],'sent':identity[2],'received_at':now,'verification':verification,'blocks':blocks}
            self.items={k:v for k,v in sorted(self.items.items(),key=lambda item:item[1]['received_at'],reverse=True)[:150]}
    def public(self,now=None,include_resources=False):
        from .alert_titles import headline,display_title
        now=now or time.time()
        with self.lock:
            active=[];immediate=[];language_excluded=0
            for item in self.items.values():
                if not self.enabled:break
                for block in item['blocks']:
                    if block['effective']<=now<block['expires']:
                        if not english(block.get('language')):
                            language_excluded+=1
                            continue
                        row={k:v for k,v in item.items() if k!='blocks'}|block
                        if not include_resources:
                            row['audio_resources']=[{k:v for k,v in r.items() if k not in ('inline','uri')} for r in row.get('audio_resources',[])]
                        if item.get('verification',{}).get('verified') is not True:continue
                        row['display_headline']=headline(row)
                        row['display_event']=display_title(row.get('event',''),row.get('language','en-CA'))
                        if block['broadcast_immediate']:immediate.append(row)
                        else:active.append(row)
            fresh=any(f['connected'] and f['heartbeat_at'] and now-f['heartbeat_at']<150 for f in self.feeds.values())
            return {'running':self.running,'fresh':bool(fresh),'coverage':'Newfoundland and Labrador','alerts':sorted(active,key=lambda x:x['sent'],reverse=True),'immediate':sorted(immediate,key=lambda x:x['sent'],reverse=True),'immediate_excluded':0,'presentation_language':'English only','language_excluded':language_excluded,'feeds':{k:dict(v) for k,v in self.feeds.items()},'archive_pending':len(self.archive_pending),'archive_checked':self.archive_checked,'archive_error':self.archive_error,'pending_recovery':len(self.pending),'recovered':self.recovered,'recovery_error':self.recovery_error,'signature_verified':True,'verified_messages':self.verified,'verification_failures':self.rejected,'verification_error':self.verification_error,'enabled':self.enabled,'automatic_playout':self.enabled,'notice':'Only NAADS-DSS authenticated English alerts enter pages, graphics and speech. Other language versions are excluded from presentation; authenticated records and cancellation processing are retained. Heartbeats are unsigned transport health, not proof of complete coverage. This is not a certified Alert Ready decoder.'}
    def persist(self):
        with self.lock:
            if not self.dirty:return
            now=time.time();self.items={k:v for k,v in self.items.items() if any(b['expires']>now for b in v['blocks'])}
            self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps({'schema':2,'trust_fingerprint':self.trust_fingerprint,'items':self.items,'retired':list(self.retired.items()),'seen':list(self.seen.items())}),encoding='utf-8');tmp.replace(self.path);self.dirty=False
    async def fetch_bytes(self,client,url,limit=MAX_BYTES):
        content=bytearray()
        async with client.stream('GET',url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content)>limit:raise ValueError('NAADS response exceeds size limit')
        return bytes(content)
    async def archive_index(self,client):
        # Startup gap recovery only. GeoRSS discovers URLs; its summaries never
        # enter alert state. Every downloaded CAP passes the normal DSS gate.
        for host in ('rss1','rss2'):
            try:
                root=safe_xml(await self.fetch_bytes(client,'https://'+host+'.naad-adna.pelmorex.com/',16*1024*1024))
                if root.tag!='{http://www.w3.org/2005/Atom}feed':raise ValueError('Expected NAADS Atom index')
                paths=[]
                for link in root.findall('.//{http://www.w3.org/2005/Atom}entry/{http://www.w3.org/2005/Atom}link'):
                    url=urlsplit(link.get('href',''))
                    if url.hostname in REPOSITORIES and re.fullmatch(r'/\d{4}-\d{2}-\d{2}/[A-Za-z0-9_.%]+\.xml',url.path):paths.append(url.path)
                if len(set(paths))>2000:raise ValueError('Archive index exceeds recovery capacity')
                with self.lock:
                    self.archive_pending.update((p,0) for p in paths);self.archive_checked=time.time();self.archive_error=None
                return
            except Exception as exc:self.archive_error=public_error(exc)[:160]
        self.archive_retry=time.time()+300
    async def stream(self,host):
        delay=2
        while True:
            writer=None
            try:
                reader,writer=await asyncio.wait_for(asyncio.open_connection(host,8080,limit=65536),15)
                if self.disconnected_since[host] and time.time()-self.disconnected_since[host]>150:self.archive_requested=True
                self.disconnected_since[host]=None
                self.feeds[host].update(connected=True,error=None,heartbeat_at=None);framer=Framer();delay=2;connected_at=time.time()
                while True:
                    chunk=await asyncio.wait_for(reader.read(32768),150)
                    if not chunk:raise ConnectionError('Feed closed; reconnecting')
                    for packet in framer.feed(chunk):
                        try:await asyncio.to_thread(self.ingest,packet,host)
                        except (ValueError,ET.ParseError) as exc:self.feeds[host]['error']=public_error(exc)[:160]
                    if time.time()-(self.feeds[host]['heartbeat_at'] or connected_at)>150:raise ConnectionError('Heartbeat timeout; reconnecting')
            except asyncio.CancelledError:raise
            except Exception as exc:self.feeds[host].update(connected=False,error=public_error(exc)[:160] or type(exc).__name__)
            finally:
                self.feeds[host]['connected']=False
                if self.disconnected_since[host] is None:self.disconnected_since[host]=time.time()
                if writer:
                    writer.close()
                    try:await writer.wait_closed()
                    except Exception:pass
            await asyncio.sleep(delay);delay=min(delay*2,60)
    async def recovery(self):
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
            await self.archive_index(client)
            while True:
                if self.archive_requested or (self.archive_checked is None and time.time()>=self.archive_retry):
                    self.archive_requested=False;await self.archive_index(client)
                with self.lock:pending=next(((k,r) for k,r in self.pending.items() if self.retry_at.get(k,0)<=time.time()),None)
                if pending:
                    key,reference=pending;success=False
                    for host in REPOSITORIES:
                        try:
                            content=bytearray()
                            async with client.stream('GET','https://'+host+repository_path(reference)) as response:
                                response.raise_for_status()
                                async for chunk in response.aiter_bytes():
                                    content.extend(chunk)
                                    if len(content)>MAX_BYTES:raise ValueError('Repository message too large')
                            root=safe_xml(content)
                            identity=tuple(root.findtext('c:'+f,default='',namespaces=NS) for f in ('sender','identifier','sent'))
                            if identity!=reference:raise ValueError('Repository identity mismatch')
                            await asyncio.to_thread(self.ingest,bytes(content),host);success=True;self.recovered+=1;self.recovery_error=None;break
                        except Exception as exc:self.recovery_error=public_error(exc)[:160]
                    with self.lock:
                        if success:self.pending.pop(key,None);self.retry_at.pop(key,None)
                        else:self.retry_at[key]=time.time()+60
                else:
                    with self.lock:archive=next(((p,t) for p,t in self.archive_pending.items() if t<=time.time()),None)
                    if archive:
                        path,_=archive;success=False
                        for host in REPOSITORIES:
                            try:
                                content=await self.fetch_bytes(client,'https://'+host+path)
                                await asyncio.to_thread(self.ingest,content,host);success=True;break
                            except Exception as exc:self.archive_error=public_error(exc)[:160]
                        with self.lock:
                            if success:self.archive_pending.pop(path,None)
                            else:self.archive_pending[path]=time.time()+300
                try:await asyncio.to_thread(self.persist)
                except OSError as exc:self.recovery_error='Alert cache: '+public_error(exc)[:120]
                await asyncio.sleep(2)
    async def watch(self):
        self.running=True
        tasks=[asyncio.create_task(self.stream(h)) for h in HOSTS]+[asyncio.create_task(self.recovery())]
        try:await asyncio.gather(*tasks)
        finally:
            self.running=False
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
