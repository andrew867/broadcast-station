from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import pytest
from skycam.program_clock import ProgramClock,ClockConfig,ClockRule,ClockWrite
from skycam.rundown import Rundown,RundownConfig
from skycam.rundown_library import LibraryConflict

TZ=ZoneInfo('America/St_Johns');A='a'*32;B='b'*32
def stamp(h=12,m=0,s=0):return datetime(2026,10,17,h,m,s,tzinfo=TZ).timestamp()
def playlist(id):
    return {'name':'Extended' if id==B else 'Short','config':{'cues':[{'camera':'weather','seconds':5},{'camera':'daylight','seconds':5}],'transition':'cut'}}
def clock(tmp_path,now=stamp(11,59)):
    c=ProgramClock(tmp_path,playlist,now=now)
    c.save(ClockWrite(expected_revision=0,config=ClockConfig(enabled=True,rules=[ClockRule(id='short',playlist_id=A,every_minutes=10,priority=1),ClockRule(id='long',playlist_id=B,every_minutes=20,priority=10,include_alerts=True)])),now=now)
    return c

def test_aligned_slots_priority_no_duplicates_and_restart(tmp_path):
    c=clock(tmp_path)
    assert c.upcoming(stamp(11,59))['at']==stamp()
    block=c.claim_due(now=stamp()+.2)
    assert block['name']=='Extended' and block['include_alerts']
    assert 'short' in c.history[-1]['detail']
    assert c.claim_due(now=stamp()+.7) is None
    restored=ProgramClock(tmp_path,playlist,now=stamp()+1)
    assert restored.claim_due(now=stamp()+2) is None
    assert c.claim_due(now=stamp(12,10)+1)['name']=='Short'

def test_busy_late_offset_and_missing_playlist(tmp_path):
    c=clock(tmp_path)
    assert c.claim_due(busy=True,now=stamp()+.1) is None
    assert c.history[-1]['outcome']=='skipped_busy'
    assert c.claim_due(now=stamp(12,10,6)) is None
    assert c.upcoming(stamp(12,10,6))['at']==stamp(12,20)
    c.save(ClockWrite(expected_revision=1,config=ClockConfig(enabled=True,rules=[ClockRule(id='offset',playlist_id=A,every_minutes=10,offset_minutes=5)])),now=stamp(12,11))
    assert c.upcoming(stamp(12,11))['at']==stamp(12,15)
    c.resolve=lambda id:(_ for _ in ()).throw(KeyError('Removed'))
    assert c.claim_due(now=stamp(12,15,1)) is None
    assert c.history[-1]['outcome']=='unavailable'
    with pytest.raises(ValueError):ClockRule(id='bad',playlist_id=A,every_minutes=10,offset_minutes=10)

def test_duplicate_rules_conflicts_and_corruption(tmp_path):
    c=clock(tmp_path)
    with pytest.raises(LibraryConflict):c.save(ClockWrite(expected_revision=0,config=ClockConfig()))
    rule=ClockRule(id='same',playlist_id=A)
    with pytest.raises(ValueError):ClockConfig(rules=[rule,rule])
    c.path.write_text('broken')
    restored=ProgramClock(tmp_path,playlist)
    assert restored.error and not restored.config.enabled

def test_dst_fall_repeated_hour_once_and_spring_jump(tmp_path):
    before=datetime(2026,11,1,0,59,tzinfo=TZ).timestamp()
    c=clock(tmp_path,now=before)
    first=datetime(2026,11,1,1,0,tzinfo=TZ,fold=0).timestamp()
    second=datetime(2026,11,1,1,0,tzinfo=TZ,fold=1).timestamp()
    assert second-first==3600
    assert c.claim_due(now=first+1)
    assert c.claim_due(now=second+1) is None
    spring=datetime(2027,3,14,1,59,tzinfo=TZ).timestamp()
    n=c.upcoming(spring)
    assert datetime.fromtimestamp(n['at'],TZ).hour==3

def rundown(tmp_path):
    calls=[]
    r=Rundown(tmp_path,lambda *args:calls.append(args))
    r.save(RundownConfig(cues=[{'camera':'cam1','seconds':20},{'camera':'map','seconds':20},{'camera':'cam2','seconds':20}]))
    r.action('start')
    return r,calls
def block(alerts=False):return {**playlist(A),'include_alerts':alerts,'rule_id':'short','scheduled_at':stamp()}

def test_block_once_then_next_background_cue_without_saved_changes(tmp_path):
    r,calls=rundown(tmp_path);saved=r.path.read_bytes()
    r._start_block(block());assert r.public()['block']['camera']=='weather'
    r._finish_cue();assert calls[-1][0]=='daylight'
    r._finish_cue();assert calls[-1][0]=='map' and r.block is None
    assert r.path.read_bytes()==saved
    r._finish_cue();assert calls[-1][0]=='cam2'

def test_short_suppresses_followup_long_keeps_it_and_expiry(tmp_path):
    r,calls=rundown(tmp_path);follows=[]
    r.followups=lambda camera:[{'token':'alert-1','seconds':5}] if camera=='weather' else []
    r.followup_take=lambda cue:follows.append(cue) or True
    r._start_block(block());r._finish_cue();assert not follows and calls[-1][0]=='daylight'
    r._end_block();r._start_block(block(True));r._finish_cue();assert len(follows)==1 and r.interlude
    r.followup_valid=lambda token:False
    r.advance_due();assert r.interlude is None and calls[-1][0]=='daylight'
    r._finish_cue();assert r.block is None

def test_manual_hold_cancels_block_and_failure_returns_to_loop(tmp_path):
    r,calls=rundown(tmp_path);r._start_block(block());r.pause('Operator take')
    count=len(calls);r.deadline=0;r.advance_due();assert len(calls)==count and not r.block
    r.action('start');r.ready=lambda camera:camera not in ('weather','daylight')
    r._start_block(block());assert r.block is None and calls[-1][0]=='map'

def test_running_block_uses_snapshot_and_restart_returns_to_loop(tmp_path):
    r,calls=rundown(tmp_path);r.config.resume_after_restart=True;r.save(r.config);r.action('start')
    item=block();r._start_block(item);item['config']['cues'][1]['camera']='cam4'
    r._finish_cue();assert calls[-1][0]=='daylight'
    restored=Rundown(tmp_path,lambda *args:calls.append(args))
    assert restored.resume_pending and restored.block is None
    restored.advance_due();assert calls[-1][0]=='map'

def test_clock_api_revision_validation_and_examples_preserve_loop(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    from skycam.rundown_library import RundownLibrary
    library=RundownLibrary(tmp_path);c=ProgramClock(tmp_path,library.export)
    monkeypatch.setattr(module,'rundown_library',library);monkeypatch.setattr(module,'program_clock',c)
    client=TestClient(module.app);headers={'X-Skycam-Edit':'1'}
    before=module.rundown.config.model_dump()
    assert client.post('/api/program-clock/examples').status_code==403
    examples=client.post('/api/program-clock/examples',headers=headers).json()
    client.post('/api/program-clock/examples',headers=headers)
    assert len(library.public()['items'])==2 and module.rundown.config.model_dump()==before
    pid=examples['playlists']['Short local forecast']
    body={'expected_revision':0,'config':{'enabled':True,'rules':[{'id':'test','playlist_id':pid}]}}
    assert client.put('/api/program-clock',json=body,headers=headers).status_code==200
    assert client.put('/api/program-clock',json=body,headers=headers).status_code==409

def test_tick_claims_clock_preempts_loop_and_returns_without_replay(tmp_path,monkeypatch):
    r,calls=rundown(tmp_path);r.clock=clock(tmp_path)
    monkeypatch.setattr('skycam.program_clock.time.time',lambda:stamp()+.2)
    r.advance_due()
    assert calls[-1][0]=='weather' and r.block['name']=='Extended'
    assert r.index==1
    r.deadline=0;r.advance_due();assert calls[-1][0]=='daylight'
    r.deadline=0;r.advance_due();assert calls[-1][0]=='map' and r.block is None
    count=len(calls);r.advance_due();assert len(calls)==count

def test_tick_manual_hold_and_alert_interlude_skip_clock(tmp_path,monkeypatch):
    r,calls=rundown(tmp_path);r.clock=clock(tmp_path)
    monkeypatch.setattr('skycam.program_clock.time.time',lambda:stamp()+.2)
    r.pause();count=len(calls);r.advance_due()
    assert len(calls)==count and not r.clock.history
    r.enabled=True;r.interlude={'token':'current','seconds':30}
    r.advance_due()
    assert len(calls)==count and r.clock.history[-1]['outcome']=='skipped_busy'
