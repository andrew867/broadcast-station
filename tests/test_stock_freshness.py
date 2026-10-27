import json
import time
from skycam.live_markets import LiveMarkets, STOCK_MAX_AGE, STOCK_RETAIN_AGE
from skycam.markets import Markets


def test_stock_boundaries_keep_timestamp_without_claiming_session(tmp_path):
    m=Markets(tmp_path)
    m.live.ingest({'type':'trade','data':[{'s':'AAPL','p':123,'t':1000000}]},1000)
    for age,status,fresh in [(120,'recent',True),(1800,'recent',True),(1801,'last_quote',False),(3*86400,'last_quote',False)]:
        row=next(r for r in m.public(1000+age)['cards'] if r['id']=='aapl')
        assert row['available'] and row['value']==123 and row['observed_at']==1000
        assert row['quote_status']==status and row['fresh']==fresh
        assert row['max_age_seconds']==STOCK_MAX_AGE
    expired=next(r for r in m.public(1001+STOCK_RETAIN_AGE)['cards'] if r['id']=='aapl')
    assert not expired['available'] and expired['value'] is None
    assert not next(r for r in m.public(1000)['cards'] if r['id']=='msft')['available']


def test_stock_cache_restores_actual_time_not_restart_time(tmp_path):
    now=time.time();path=tmp_path/'quotes.json'
    path.write_text(json.dumps([{'s':'AAPL','p':123,'t':(now-3*86400)*1000}, {'s':'MSFT','p':0,'t':now*1000}, {'s':'NVDA','p':12,'t':(now-8*86400)*1000}]))
    live=LiveMarkets('',cache_path=path)
    row=live.public(now)['quotes']['aapl']
    assert row['value']==123 and row['quote_status']=='last_quote' and row['cached']
    assert abs(row['observed_at']-(now-3*86400))<.01
    assert set(live.public(now)['quotes'])=={'aapl'}
    live.ingest({'type':'trade','data':[{'s':'AAPL','p':124,'t':now*1000}]},now)
    assert LiveMarkets('',cache_path=path).public(now)['quotes']['aapl']['value']==124
