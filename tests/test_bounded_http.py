import asyncio,gzip
import httpx,pytest
from skycam.bounded_http import bounded_get,bounded_get_sync


def test_compressed_reply_is_limited_after_decompression():
    def reply(request):return httpx.Response(200,content=gzip.compress(b'x'*10000),headers={'content-encoding':'gzip'})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        with pytest.raises(ValueError,match='size limit'):bounded_get_sync(client,'https://example.com',max_bytes=500)


def test_async_json_retains_status_and_decoded_content():
    async def check():
        def reply(request):return httpx.Response(200,content=gzip.compress(b'{"value":12}'),headers={'content-encoding':'gzip','content-type':'application/json'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            response=await bounded_get(client,'https://example.com')
            assert response.json()=={'value':12} and 'content-encoding' not in response.headers
            with pytest.raises(ValueError,match='size limit'):await bounded_get(client,'https://example.com',max_bytes=5)
    asyncio.run(check())
