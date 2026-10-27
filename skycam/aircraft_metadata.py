"""Bounded local SkyAware database lookups, separate from position reception."""
import asyncio
from collections import OrderedDict
import os
import re
import threading
import time

import httpx


class AircraftMetadata:
    def __init__(self, base=None):
        self.base=(base or os.environ.get('SKYCAM_METADATA_BASE',
            'http://192.0.2.30:8080/skyaware/db/')).rstrip('/')+'/'
        self.lock=threading.RLock();self.cache=OrderedDict();self.pending=OrderedDict()
        self.blocks=OrderedDict();self.error=None;self.lookups=0

    def lookup(self, hex_id, now=None):
        now=time.time() if now is None else now
        key=str(hex_id).upper()
        if not re.fullmatch('[0-9A-F]{6}',key):return {}
        with self.lock:
            cached=self.cache.get(key)
            if cached and 0<=now-cached['checked_at']<86400:
                return dict(cached['data'])
            self.pending[key]=None
            while len(self.pending)>64:self.pending.popitem(last=False)
            return {}

    def fetch(self, key, client):
        for level in range(1,7):
            prefix=key[:level]
            cached=self.blocks.get(prefix)
            if cached and time.time()-cached[0]<86400:
                data=cached[1];self.blocks.move_to_end(prefix)
            else:
                content=bytearray()
                with client.stream('GET',self.base+prefix+'.json') as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content)>2*1024*1024:raise ValueError('Metadata block exceeds limit')
                import json
                data=json.loads(content)
                if not isinstance(data,dict):raise ValueError('Invalid aircraft metadata block')
                self.blocks[prefix]=(time.time(),data)
                while len(self.blocks)>16:self.blocks.popitem(last=False)
            row=data.get(key[level:])
            if isinstance(row,dict):
                result={}
                for source,dest in [('t','aircraft_type'),('r','registration')]:
                    value=row.get(source)
                    if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9 -]{1,16}',value):result[dest]=value.strip()
                if result:result['metadata_source']='LOCAL SKYAWARE DATABASE'
                return result
            if key[:level+1] not in data.get('children',[]):break
        return {}

    def process_one(self):
        with self.lock:
            if not self.pending:return
            key,_=self.pending.popitem(last=False)
        try:
            with httpx.Client(timeout=3,trust_env=False,follow_redirects=False) as client:
                result=self.fetch(key,client)
            with self.lock:
                self.error=None;self.lookups+=1
                self.cache[key]={'checked_at':time.time(),'data':result}
                while len(self.cache)>2000:self.cache.popitem(last=False)
        except (ValueError,httpx.HTTPError) as exc:
            with self.lock:
                self.error='Aircraft metadata unavailable ('+type(exc).__name__+')'
                # Retry failures after one minute, without starving other IDs.
                self.cache[key]={'checked_at':time.time()-86400+60,'data':{}}
                while len(self.cache)>2000:self.cache.popitem(last=False)

    def public(self):
        with self.lock:return {'source':'Local SkyAware database','cached_aircraft':len(self.cache),
            'pending':len(self.pending),'lookups':self.lookups,'error':self.error,
            'note':'Database identity metadata; not a flight plan or live route.'}

    async def watch(self):
        while True:
            await asyncio.to_thread(self.process_one)
            await asyncio.sleep(1)
