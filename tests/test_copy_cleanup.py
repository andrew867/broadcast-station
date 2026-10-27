import json,time
import pytest
from skycam.broadcast import Broadcast,BroadcastState,clean_legacy_copy
from skycam.rundown import Rundown,RundownConfig

def legacy(**kw):
    return BroadcastState(headline="THE SKY ABOVE ST. JOHN’S",kicker='ACROSS THE CITY',
        subline='Live views from St. John’s, Quidi Vidi Lake and Torbay',**kw)

def test_stock_migration_is_exact_and_keeps_operator_fields(tmp_path):
    b=Broadcast(tmp_path);old=legacy(ticker_speed=237,show_lower=False)
    b.save(old);reloaded=Broadcast(tmp_path)
    assert reloaded.state.headline==reloaded.state.kicker==reloaded.state.subline==''
    assert reloaded.state.ticker_speed==237 and not reloaded.state.show_lower
    archive=b.path.with_name('state-before-copy-cleanup.json')
    assert json.loads(archive.read_text(encoding="utf-8"))['headline']==old.headline
    assert Broadcast(tmp_path).state==reloaded.state
    custom=old.model_copy(update={'headline':'Airport delays','kicker':'TRAVEL','subline':'Check your flight'})
    assert clean_legacy_copy(custom)==custom
    assert clean_legacy_copy(legacy(scene='breaking')).headline==old.headline
    mixed=old.model_copy(update={'subline':'Operator message'})
    assert clean_legacy_copy(mixed).subline=='Operator message'

def setup(tmp_path,ids):
    calls=[];prepared=[];r=Rundown(tmp_path,lambda *a:calls.append(a),prepare=lambda *a:prepared.append(a))
    r.save(RundownConfig(cues=[{'camera':c,'seconds':20} for c in ids]))
    inactive={'advertisement','community-notices'}
    r.eligible=lambda c:c not in inactive
    return r,calls,prepared,inactive

def test_empty_assets_skip_while_camera_fallback_remains_selectable(tmp_path):
    r,calls,prepared,inactive=setup(tmp_path,['advertisement','community-notices','cam1','map'])
    r.action('start');assert calls[-1][0]=='cam1'
    r.deadline=time.monotonic()+3;r.advance_due();assert prepared[-1][0]=='map'
    inactive.clear();r.action('start');assert calls[-1][0]=='advertisement'
    # Manual apply is independent of automatic eligibility.
    inactive.add('advertisement');r.pause();r.apply('advertisement','standard',0)
    assert calls[-1][0]=='advertisement' and not r.enabled

def test_all_empty_background_falls_back_without_stopping(tmp_path):
    r,calls,_,_=setup(tmp_path,['community-notices','advertisement'])
    r.action('start');assert r.enabled and calls[-1][0]=='map'
    assert 0<r.deadline-time.monotonic()<=5

def test_empty_scheduled_block_returns_to_background_once(tmp_path):
    r,calls,_,_=setup(tmp_path,['cam1','map'])
    r.action('start')
    r._start_block({'name':'Notices','include_alerts':False,'rule_id':'test','scheduled_at':time.time(),
        'config':{'cues':[{'camera':'community-notices','seconds':10},{'camera':'advertisement','seconds':10}]}})
    assert r.block is None and calls[-1][0]=='map' and len(calls)==2

def test_empty_prepared_clock_block_is_not_loaded(tmp_path):
    r,calls,prepared,_=setup(tmp_path,['cam1','map']);r.action('start')
    class Clock:
        def claim_due(self,**kw):return None
        def upcoming(self):return {'at':time.time()+4,'slot':'one','rule':{'playlist_id':'empty'}}
        def resolve(self,_):return {'config':{'cues':[{'camera':'advertisement','seconds':5}]}}
    r.clock=Clock();r.advance_due();assert not prepared

