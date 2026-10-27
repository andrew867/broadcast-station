"""Limit decompressed provider replies before allocating/parsing the complete body."""
import asyncio,time
import httpx


def complete(response,body):
    headers=dict(response.headers)
    for name in ('content-encoding','content-length','transfer-encoding'):headers.pop(name,None)
    return httpx.Response(response.status_code,headers=headers,content=bytes(body),request=response.request)


async def bounded_get(client,url,*,max_bytes=2_000_000,**kwargs):
    async with asyncio.timeout(30):
        async with client.stream('GET',url,**kwargs) as response:
            response.raise_for_status();body=bytearray()
            async for chunk in response.aiter_bytes(chunk_size=65536):
                if len(body)+len(chunk)>max_bytes:raise ValueError('Provider reply exceeds size limit')
                body.extend(chunk)
            return complete(response,body)


def bounded_get_sync(client,url,*,max_bytes=2_000_000,**kwargs):
    deadline=time.monotonic()+30
    with client.stream('GET',url,**kwargs) as response:
        response.raise_for_status();body=bytearray()
        for chunk in response.iter_bytes(chunk_size=65536):
            if time.monotonic()>deadline:raise ValueError('Provider reply timed out')
            if len(body)+len(chunk)>max_bytes:raise ValueError('Provider reply exceeds size limit')
            body.extend(chunk)
        return complete(response,body)
