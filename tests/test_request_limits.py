import asyncio
from skycam.request_limits import RequestLimits,allowed_host,JSON_BYTES

def request(chunks,headers=(),seconds=30):
    messages=[];called=[];iterator=iter(chunks)
    async def receive():
        item=next(iterator)
        if item is None:await asyncio.sleep(1)
        return item
    async def send(message):messages.append(message)
    async def app(scope,receive,send):
        called.append((await receive())['body']);await send({'type':'http.response.start','status':204,'headers':[]})
    scope={'type':'http','method':'POST','path':'/api/rundown','headers':[(b'host',b'localhost'),*headers]}
    asyncio.run(RequestLimits(app,body_seconds=seconds)(scope,receive,send))
    return messages,called

def test_chunked_oversize_never_enters_handler():
    messages,called=request([{'type':'http.request','body':b'x'*JSON_BYTES,'more_body':True},{'type':'http.request','body':b'x'}])
    assert not called and messages[0]['status']==413

def test_announced_oversize_does_not_read_body():
    messages,called=request([],[(b'content-length',str(JSON_BYTES+1).encode())]);assert not called and messages[0]['status']==413

def test_small_chunked_body_preserved():
    messages,called=request([{'type':'http.request','body':b'{','more_body':True},{'type':'http.request','body':b'}'}])
    assert called==[b'{}'] and messages[0]['status']==204

def test_slow_body_deadline():
    messages,called=request([None],seconds=.001);assert not called and messages[0]['status']==408

def test_host_rebinding_and_invalid_hosts_rejected():
    for host in ('attacker.example','localhost@attacker.example','localhost/path','0.0.0.0','224.0.0.1','localhost:999999','localhost\r\nX: yes'):
        assert not allowed_host(host)
    for host in ('localhost:8765','127.0.0.1','[::1]:8765','192.168.2.10:8765','studio'):
        assert allowed_host(host)
    assert allowed_host('station.example',('station.example',))
