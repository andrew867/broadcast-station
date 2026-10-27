import asyncio
import json
from datetime import datetime,timezone

import httpx
import pytest

from skycam.tmx_markets import TmxMarkets,parse_quote,parse_history,MAX_RECEIPT_AGE,MAX_BYTES
from skycam.markets import Markets
from skycam.market_graphics import image

NOW=datetime(2026,10,19,20,tzinfo=timezone.utc).timestamp()

def quote(**changes):
    return {'data':{'getQuoteBySymbol':dict(symbol='^TSX',datatype='index',price=10100,
        prevClose=10000,priceChange=100,percentChange=1,**changes)}}

def history():
    return {'data':{'getIndexPriceHistory':[
        {'datetime':'2026-10-19','closePrice':10100},
        {'datetime':'2026-10-16','closePrice':10000}]}}

@pytest.mark.parametrize('key,value',[('symbol','TSX'),('datatype','equity'),('price',0),
    ('price',float('nan')),('price',True),('prevClose',None),('priceChange',200),('percentChange',50)])
def test_reject_bad_quote(key,value):
    payload=quote();payload['data']['getQuoteBySymbol'][key]=value
    with pytest.raises(ValueError):parse_quote(payload)

def test_graphql_error_even_with_data_is_not_success():
    payload=quote();payload['errors']=[{'message':'unauthorized'}]
    with pytest.raises(ValueError):parse_quote(payload)
    with pytest.raises(ValueError):parse_quote({'data':{'getQuoteBySymbol':None}})

def test_daily_history_sorted_and_not_a_quote_timestamp():
    rows=parse_history(history(),NOW)
    assert [r['date'] for r in rows]==['2026-10-16','2026-10-19']
    payload=history();payload['data']['getIndexPriceHistory'][0]['datetime']='2026-10-20'
    with pytest.raises(ValueError):parse_history(payload,NOW)

def test_opt_in_requires_both_flags(tmp_path):
    assert not TmxMarkets(tmp_path).enabled
    folder=tmp_path/'broadcast';folder.mkdir()
    config=folder/'tmx-config.json'
    config.write_text(json.dumps({'enabled':True}))
    assert not TmxMarkets(tmp_path).enabled
    config.write_text(json.dumps({'enabled':True,'redistribution_confirmed':True}))
    assert TmxMarkets(tmp_path).enabled

def test_refresh_expiry_and_independent_history_failure(tmp_path):
    async def run():
        feed=TmxMarkets(tmp_path,True);calls=[];failed=set()
        def handler(req):
            op=json.loads(req.content)['operationName'];calls.append(op)
            if op in failed:return httpx.Response(200,json={'errors':[{'message':'oops'}]})
            return httpx.Response(200,json=quote() if op=='getQuoteBySymbol' else history())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await feed.refresh(client,NOW)
            row=feed.public(NOW)
            assert row['available'] and row['change']==100 and row['change_percent']==1
            assert row['observed_at'] is None and row['delay_seconds'] is None
            assert row['received_at']==NOW and row['history'][-1]['date']=='2026-10-19'
            row['history'].clear();assert len(feed.public(NOW)['history'])==2
            await feed.refresh(client,NOW+120)
            assert calls.count('getIndexPriceHistory')==1
            failed.add('getQuoteBySymbol');await feed.refresh(client,NOW+240)
            assert feed.public(NOW+240)['cached'] and feed.public(NOW+240)['available']
            stale=feed.public(NOW+120+MAX_RECEIPT_AGE)
            assert not stale['available'] and stale['value'] is None and not stale['history']
            assert not feed.public(NOW-1)['available']
            failed.clear();failed.add('getIndexPriceHistory');await feed.refresh(client,NOW+4000)
            assert feed.public(NOW+4000)['available'] and not feed.public(NOW+4000)['history']
    asyncio.run(run())

@pytest.mark.parametrize('mode',['large','http','json'])
def test_bad_transport_is_bounded_and_contained(tmp_path,mode):
    async def run():
        feed=TmxMarkets(tmp_path,True)
        def handler(req):
            return httpx.Response(429 if mode=='http' else 200,content=b'x'*(MAX_BYTES+1) if mode=='large' else b'not json')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await feed.refresh(client,NOW)
        assert not feed.public(NOW)['available'] and len(feed.errors)==2
    asyncio.run(run())

def test_markets_integration_keeps_three_pages_and_no_fake_timing(tmp_path):
    markets=Markets(tmp_path);markets.tmx=TmxMarkets(tmp_path,True)
    feed=markets.tmx;feed.quote=parse_quote(quote());feed.received_at=NOW
    feed.history=parse_history(history(),NOW);feed.history_received_at=NOW
    data=markets.public(NOW)
    assert len(data['pages'])==3 and data['pages'][0]==['tsx','fx','wti','brent']
    assert data['cards'][-1]['unit']=='INDEX POINTS'
    assert image(data).size==(3840,2160)
    assert image(markets.public(NOW+MAX_RECEIPT_AGE)).size==(3840,2160)
