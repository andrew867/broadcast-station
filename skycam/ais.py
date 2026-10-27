from .station_config import secret
"""Bounded server-side AISStream receiver. Never expose credentials to clients."""
import asyncio,json,math,os,random,re,threading,time
from collections import deque
from datetime import datetime
from pydantic import Field
from .models import StrictModel
from .storage import save_json

ENDPOINT='wss://stream.aisstream.io/v0/stream'
BOX=[[[43,-60],[53,-45]]]
LONG_RANGE='LongRangeAisBroadcastMessage'
POSITION_TYPES=('PositionReport','StandardClassBPositionReport','ExtendedClassBPositionReport',LONG_RANGE)

class AisConfig(StrictModel):
    enabled:bool=True
    show_on_maps:bool=False
    show_trails:bool=True

def timestamp(value):
    if not isinstance(value,str):raise ValueError('Missing AIS observation time')
    # AISStream currently sends a Go time string with nanosecond precision.
    match=re.fullmatch(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(?:\.(\d+))? ([+-]\d{4}) UTC',value)
    if match:value=match[1]+'.'+(match[2] or '0')[:6]+match[3]
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('AIS observation time lacks timezone')
    return d.timestamp()

def number(value,low,high):
    if isinstance(value,bool):return None
    try:f=float(value)
    except (TypeError,ValueError):return None
    return f if math.isfinite(f) and low<=f<=high else None

def name(value):return ''.join(c for c in str(value or '') if c.isprintable()).strip(' @')[:40]

class Ais:
    def __init__(self,data):
        self.path=data/'broadcast/ais.json';self.lock=threading.RLock()
        self.config=AisConfig.model_validate_json(self.path.read_text()) if self.path.exists() else AisConfig()
        self.key=(secret('aisstream') or os.environ.get('AISSTREAM_API_KEY','')).strip()
        self.vessels={};self.static={};self.connected=False;self.compressed=False;self.error=None
        self.received=0;self.rejected=0;self.last_message_at=0;self.last_position_at=0;self.reconnects=0;self.position_types={}
        self.message_types={};self.accepted_positions=0;self.duplicate_positions=0;self.coarse_held=0
    def save(self,config):
        with self.lock:save_json(self.path,config.model_dump());self.config=config
    def ingest(self,data,now=None):
        now=time.time() if now is None else now
        if data.get('error') or data.get('Error'):raise ValueError('AIS service rejected subscription')
        kind=data.get('MessageType');body=data.get('Message',{})
        if kind=='SubscriptionConfirmation':
            self.compressed=body.get('CompressionEnabled') is True;return
        if kind not in (*POSITION_TYPES,'ShipStaticData'):return
        meta=data.get('MetaData',{});p=body.get(kind,{})
        if p.get('Valid') is not True:raise ValueError('Invalid AIS message')
        mmsi=str(p.get('UserID',''))
        if not re.fullmatch(r'[1-9][0-9]{8}',mmsi) or str(meta.get('MMSI'))!=mmsi:raise ValueError('Invalid AIS identity')
        at=timestamp(meta.get('time_utc'))
        if not -30<=now-at<=1800:raise ValueError('AIS observation is stale or in the future')
        with self.lock:
            self.last_message_at=now;self.received+=1
            self.message_types[kind]=self.message_types.get(kind,0)+1
            if kind=='ShipStaticData':
                self.static[mmsi]={'name':name(p.get('Name')),'callsign':name(p.get('CallSign')),'ship_type':p.get('Type'),'at':at}
                if len(self.static)>1000:self.static.pop(min(self.static,key=lambda k:self.static[k]['at']))
                return
            lat=number(p.get('Latitude'),43,53);lon=number(p.get('Longitude'),-60,-45)
            if lat is None or lon is None:raise ValueError('AIS position unavailable or outside subscription')
            previous=self.vessels.get(mmsi)
            if previous and at<=previous['at']:
                self.duplicate_positions+=1;return
            self.position_types[kind]=self.position_types.get(kind,0)+1
            long_range=kind==LONG_RANGE
            # A coarse long-range report must not displace a recent detailed fix.
            if long_range and previous and not previous.get('long_range') and now-previous['at']<=300:
                self.coarse_held+=1;return
            trail=previous['trail'] if previous else deque(maxlen=40)
            if long_range or (previous and previous.get('long_range')):trail.clear()
            if trail and (at-trail[-1][0]>180 or abs(lat-trail[-1][1])>0.15 or abs(lon-trail[-1][2])>.2):trail.clear()
            if not trail or at-trail[-1][0]>=15:trail.append((at,lat,lon))
            while trail and at-trail[0][0]>600:trail.popleft()
            info=self.static.get(mmsi,{})
            self.vessels[mmsi]={'mmsi':mmsi,'name':name(meta.get('ShipName')) or info.get('name') or mmsi,
                'lat':lat,'lon':lon,'sog':number(p.get('Sog'),0,62 if long_range else 102.2),'cog':number(p.get('Cog'),0,359 if long_range else 359.9),
                'message_type':kind,'long_range':long_range,'position_latency':p.get('PositionLatency') if long_range else None,
                'heading':number(p.get('TrueHeading'),0,359),'at':at,'received_at':now,'trail':trail}
            self.last_position_at=now
            self.accepted_positions+=1
            self.vessels={k:v for k,v in self.vessels.items() if now-v['at']<1800}
            if len(self.vessels)>500:self.vessels.pop(min(self.vessels,key=lambda k:self.vessels[k]['at']))
    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            rows=[]
            for v in self.vessels.values():
                age=max(0,now-v['at'])
                if age>=1800:continue
                rows.append({**v,'age_s':round(age),'stale':age>300,
                    'trail':[[q[1],q[2]] for q in v['trail'] if now-q[0]<=600] if self.config.show_trails and not v.get('long_range') else []})
            rows.sort(key=lambda v:(v['stale'],v['name']))
            counts={'recent':len(rows),'fresh':sum(not v['stale'] for v in rows),
                    'moving_fresh':sum(not v['stale'] and (v['sog'] or 0)>.5 for v in rows),
                    'older':sum(v['stale'] for v in rows)} if self.config.enabled else dict.fromkeys(('recent','fresh','moving_fresh','older'),0)
            positioned={r['mmsi'] for r in rows}
            return {'config':self.config.model_dump(),'configured':bool(self.key),'connected':self.connected,
                'compression':self.compressed,'source':'AISStream','source_url':'https://aisstream.io/',
                'vessels':rows if self.config.enabled else [],'counts':counts,'last_position_at':self.last_position_at or None,
                'received':self.received,'rejected':self.rejected,'reconnects':self.reconnects,'error':self.error,
                'position_types':dict(self.position_types),'subscribed_position_types':list(POSITION_TYPES),
                'diagnostics':{'validated_messages_by_type':dict(self.message_types),
                    'position_updates_applied':self.accepted_positions,'duplicate_or_older_positions':self.duplicate_positions,
                    'coarse_positions_held':self.coarse_held,
                    'static_only_recent':sum(0<=now-v['at']<1800 and mmsi not in positioned for mmsi,v in self.static.items())},
                'subscription_bounds':{'south':43,'north':53,'west':-60,'east':-45},
                'note':'Provider receipt times, not a guaranteed vessel transmission clock. Coverage is incomplete. Not for navigation.'}
    async def watch(self):
        from websockets.asyncio.client import connect
        delay=2
        while True:
            if not self.key or not self.config.enabled:
                self.connected=False;await asyncio.sleep(2);continue
            try:
                async with connect(ENDPOINT,compression='deflate',proxy=None,open_timeout=10,
                    ping_interval=20,ping_timeout=20,close_timeout=3,max_size=65536,max_queue=32) as ws:
                    await ws.send(json.dumps({'APIKey':self.key,'BoundingBoxes':BOX,
                        'FilterMessageTypes':[*POSITION_TYPES,'ShipStaticData']}))
                    self.connected=True;self.error=None;opened=time.monotonic()
                    while self.config.enabled:
                        try:raw=await asyncio.wait_for(ws.recv(),5)
                        except TimeoutError:continue
                        try:self.ingest(json.loads(raw))
                        except (ValueError,TypeError,KeyError):
                            self.rejected+=1
                            # Server status errors must reconnect; data errors are skipped.
                            if b'"error"' in (raw.encode() if isinstance(raw,str) else raw).lower():raise ValueError('AIS subscription rejected')
                        if time.monotonic()-opened>60:delay=2
            except asyncio.CancelledError:raise
            except Exception as exc:
                # Exception payloads can echo the subscription. Never log them.
                self.error='AIS connection interrupted ('+type(exc).__name__+'); reconnecting'
                self.reconnects+=1
            finally:self.connected=False;self.compressed=False
            await asyncio.sleep(delay+random.uniform(0,1));delay=min(60,delay*2)
