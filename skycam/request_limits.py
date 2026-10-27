"""Bound operator requests before JSON parsing; reject browser DNS rebinding hosts."""
import asyncio
import ipaddress
import os
import re
import socket
from urllib.parse import urlsplit
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

JSON_BYTES=2*1024*1024

def body_limit(path):
    if path=='/api/commercial/assets':return 100*1024*1024
    if path=='/api/notices/images' or re.fullmatch(r'/api/source-catalog/[a-z0-9_-]{1,48}/reference',path):return 16*1024*1024
    return JSON_BYTES

def allowed_host(value,extra=()):
    try:
        if any(ord(c)<33 for c in value) or any(c in value for c in '/\\@?#'):return False
        parsed=urlsplit('http://'+value);name=parsed.hostname
        if not name or (parsed.port is not None and not 1<=parsed.port<=65535):return False
        if name.lower() in {'localhost','studio',socket.gethostname().lower(),*(x.strip().lower() for x in extra)}:return True
        address=ipaddress.ip_address(name)
        return address.is_loopback or (address.is_private and not address.is_unspecified and not address.is_multicast and not address.is_link_local)
    except (ValueError,TypeError):return False

class RequestLimits:
    def __init__(self,app,allowed_hosts=None,body_seconds=30):
        self.app=app;self.hosts=allowed_hosts if allowed_hosts is not None else os.environ.get('STATION_ALLOWED_HOSTS','').split(',');self.seconds=body_seconds
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers=scope.get('headers',[])
        hosts=[v for k,v in headers if k.lower()==b'host']
        if len(hosts)!=1 or not allowed_host(hosts[0].decode('ascii',errors='replace'),self.hosts):
            return await JSONResponse({'detail':'Unconfigured operator host'},status_code=400)(scope,receive,send)
        limit=body_limit(scope['path']);lengths=[v for k,v in headers if k.lower()==b'content-length']
        if len(lengths)>1 or (lengths and not re.fullmatch(rb'[0-9]{1,12}',lengths[0])):
            return await JSONResponse({'detail':'Invalid request length'},status_code=400)(scope,receive,send)
        if lengths and int(lengths[0])>limit:
            return await JSONResponse({'detail':'Request exceeds size limit'},status_code=413)(scope,receive,send)
        if scope['method'] in ('GET','HEAD','OPTIONS'):return await self.app(scope,receive,send)
        # Small control bodies are bounded before FastAPI/Pydantic allocates JSON.
        # Large media uploads keep streaming to the existing bounded file handlers.
        if limit==JSON_BYTES:
            body=bytearray()
            try:
                async with asyncio.timeout(self.seconds):
                    while True:
                        message=await receive()
                        if message['type']=='http.disconnect':return
                        chunk=message.get('body',b'')
                        if len(body)+len(chunk)>limit:
                            return await JSONResponse({'detail':'Request exceeds size limit'},status_code=413)(scope,receive,send)
                        body.extend(chunk)
                        if not message.get('more_body',False):break
            except TimeoutError:
                return await JSONResponse({'detail':'Request body timed out'},status_code=408)(scope,receive,send)
            delivered=False
            async def buffered():
                nonlocal delivered
                if not delivered:delivered=True;return {'type':'http.request','body':bytes(body),'more_body':False}
                return await receive()
            return await self.app(scope,buffered,send)
        count=0;deadline=asyncio.get_running_loop().time()+120
        async def bounded():
            nonlocal count
            try:message=await asyncio.wait_for(receive(),max(.001,deadline-asyncio.get_running_loop().time()))
            except TimeoutError:raise HTTPException(408,'Upload timed out') from None
            count+=len(message.get('body',b''))
            if count>limit:raise HTTPException(413,'Upload exceeds size limit')
            return message
        return await self.app(scope,bounded,send)
