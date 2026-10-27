from datetime import datetime,timezone
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from skycam.aeroapi import AeroAPI,Unavailable,money

NOW=datetime(2026,10,20,18,tzinfo=timezone.utc).timestamp()

def make(tmp_path, cost=0, fail=False):
    calls=[]
    def transport(path,params):
        calls.append((path,params))
        if path=='account/usage':return {'total_cost':cost}
        if fail:raise Unavailable('timeout')
        return {'flights':[], 'links':{'next':'never-follow'},'num_pages':1}
    client=AeroAPI(tmp_path/'state',tmp_path/'key',transport,lambda:NOW)
    return client,calls

def arm(client):
    client.policy.write_text(json.dumps({'enabled':True,'period':'2026-10',
        'confirmed_credit_usd':10,'pricing_verified':'2026-10-20'}))

def test_disabled_default_never_calls_provider(tmp_path):
    client,calls=make(tmp_path)
    with pytest.raises(Unavailable,match='disabled'):client.lookup('ACA123')
    assert calls==[]

def test_one_page_cache_and_durable_reservation(tmp_path):
    client,calls=make(tmp_path);arm(client)
    assert not client.lookup('ACA123')['cached']
    assert client.lookup('ACA123')['cached']
    assert len(calls)==2 and calls[1][1]['max_pages']==1
    assert calls[0][1]['all_keys']=='true'
    assert client.status()['local_reserved_usd']==.005
    again=AeroAPI(client.folder,client.key_file,client.transport,lambda:NOW)
    assert again.status()['local_reserved_usd']==.005

def test_failed_call_stays_reserved(tmp_path):
    client,calls=make(tmp_path,fail=True);arm(client)
    with pytest.raises(Unavailable):client.lookup('ACA123')
    assert client.status()['local_reserved_usd']==.005
    assert len(calls)==2

@pytest.mark.parametrize('cost',[8,7.999,None,-1,'NaN','Infinity'])
def test_budget_and_invalid_usage_fail_closed(tmp_path,cost):
    client,calls=make(tmp_path,cost);arm(client)
    with pytest.raises(Unavailable):client.lookup('ACA123')
    assert len(calls)==1 and calls[0][0]=='account/usage'
    assert client.status()['local_reserved_usd']==0

def test_missing_ledger_cannot_reset_budget(tmp_path):
    client,_=make(tmp_path);client.ledger.unlink()
    with pytest.raises(Unavailable,match='ledger missing'):
        AeroAPI(client.folder,client.key_file)

def test_month_change_requires_review(tmp_path):
    client,calls=make(tmp_path);arm(client)
    client.clock=lambda:NOW+32*86400
    with pytest.raises(Unavailable):client.lookup('ACA123')
    assert not calls

def test_parallel_limits(tmp_path):
    client,calls=make(tmp_path);arm(client)
    def lookup(n):
        try:client.lookup('ACA'+str(n));return True
        except Unavailable:return False
    with ThreadPoolExecutor(max_workers=6) as workers:
        result=list(workers.map(lookup,range(100,106)))
    assert sum(result)==2
    assert client.status()['local_reserved_usd']==.01

def test_untrusted_ident_cannot_change_endpoint(tmp_path):
    client,calls=make(tmp_path);arm(client)
    for ident in ('../account','ACA123?max_pages=9','https://bad'):
        with pytest.raises(Unavailable):client.lookup(ident)
    assert not calls

def test_microusd_rounds_up():
    assert money(.005)==5000
    assert money('0.0000001')==1
