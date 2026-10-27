"""Off-air boundary and recovery acceptance; never contacts the live engine."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from skycam.dayparts import Dayparts, DaypartConfig, DaypartWrite
from skycam.picture_history import PictureHistory, enforce_budget
from skycam.rundown import Rundown, RundownConfig
from tests.test_features import jpeg

TZ=ZoneInfo('America/St_Johns')
ID='a'*32

def stamp(value,fold=0):
    return datetime.fromisoformat(value).replace(tzinfo=TZ,fold=fold).timestamp()

def library(_):
    return {'name':'Night','config':RundownConfig(cues=[{'camera':'map','seconds':5}]).model_dump()}

def selector(tmp_path):
    d=Dayparts(tmp_path,library)
    d.save(DaypartWrite(expected_revision=0,config=DaypartConfig(enabled=True,periods=[
        {'name':'Night','playlist_id':ID,'start':'22:00','end':'07:00'}])))
    return d

def test_daypart_dst_folds_spring_jump_and_exact_edges(tmp_path):
    d=selector(tmp_path)
    for value,fold,selected in [
        ('2026-10-18T21:59:59',0,False),('2026-10-18T22:00:00',0,True),
        ('2026-10-19T00:00:00',0,True),('2026-10-19T06:59:59',0,True),
        ('2026-10-19T07:00:00',0,False),('2026-11-01T01:30:00',0,True),
        ('2026-11-01T01:30:00',1,True),('2027-03-14T01:59:59',0,True),
        ('2027-03-14T03:00:00',0,True),
    ]:
        assert bool(d.selection(stamp(value,fold))) is selected

def test_missing_daypart_returns_to_regular_loop_and_can_recover(tmp_path,monkeypatch):
    d=selector(tmp_path)
    monkeypatch.setattr('skycam.dayparts.time.time',lambda:stamp('2026-10-19T01:00'))
    takes=[];r=Rundown(tmp_path,lambda *args:takes.append(args))
    r.save(RundownConfig(cues=[{'camera':'cam1','seconds':5}]))
    saved=r.path.read_bytes();r.dayparts=d;r.action('start')
    assert takes[-1][0]=='map'
    d.resolve=lambda _:(_ for _ in ()).throw(KeyError('Playlist removed'))
    r.deadline=0;r.advance_due()
    assert takes[-1][0]=='cam1' and r.enabled and d.error
    d.resolve=library;r.deadline=0;r.advance_due()
    assert takes[-1][0]=='map' and d.error is None and r.path.read_bytes()==saved

def test_restart_waits_for_output_and_resolves_current_daypart(tmp_path,monkeypatch):
    d=selector(tmp_path)
    monkeypatch.setattr('skycam.dayparts.time.time',lambda:stamp('2026-10-19T01:00'))
    takes=[];r=Rundown(tmp_path,lambda *args:takes.append(args))
    r.save(RundownConfig(cues=[{'camera':'cam1','seconds':5},{'camera':'cam2','seconds':5}],resume_after_restart=True))
    r.action('start');r.action('next')
    available=[False]
    restored=Rundown(tmp_path,lambda *args:takes.append(args),recovery_ready=lambda:available[0])
    restored.dayparts=d;count=len(takes);restored.advance_due()
    assert restored.resume_pending and len(takes)==count
    available[0]=True;restored.advance_due()
    assert takes[-1][0]=='map' and restored.enabled and not restored.resume_pending
    restored.pause();again=Rundown(tmp_path,lambda *args:takes.append(args))
    assert not again.resume_pending

@pytest.mark.parametrize('index',[None,12,True,{'unexpected':'object'},'text'])
def test_history_recovers_non_list_index(tmp_path,index):
    (tmp_path/'index.json').write_text(json.dumps(index))
    h=PictureHistory(tmp_path)
    assert h.entries()==[]
    assert h.add(jpeg(),deduplicate=True)

def test_history_drops_incomplete_duplicate_and_nonfinite_rows(tmp_path,monkeypatch):
    monkeypatch.setattr('skycam.picture_history.time.time',lambda:1000)
    h=PictureHistory(tmp_path);h.add(jpeg(),999)
    good=h.entries()[0]
    rows=[good,good,{**good,'at':float('nan')},{**good,'at':True},
          {'at':999,'file':good['file']},{**good,'file':'../outside.jpg'}]
    h.index.write_text(json.dumps(rows))
    restored=PictureHistory(tmp_path)
    assert restored.entries()==[good]
    assert restored.add(jpeg('blue'),1000,deduplicate=True)

def test_history_skips_damaged_frame_and_retains_valid_picture(tmp_path,monkeypatch):
    monkeypatch.setattr('skycam.picture_history.time.time',lambda:1000)
    h=PictureHistory(tmp_path);h.add(jpeg(),998);h.add(jpeg('blue'),999)
    first=h.entries()[0];(tmp_path/first['file']).write_bytes(b'partial image')
    image,row=h.frame(0)
    assert image.size==(640,360) and row['at']==999
    assert len(h.entries())==1 and not (tmp_path/first['file']).exists()

def test_retention_stays_bounded_across_many_retired_cameras_and_restart(tmp_path,monkeypatch):
    tick=[1000.0];monkeypatch.setattr('skycam.picture_history.time.time',lambda:tick[0])
    histories=[PictureHistory(tmp_path/str(n),count=4,age=60,budget=10000) for n in range(12)]
    for step in range(90):
        tick[0]+=1
        for h in histories:h.add(jpeg(),tick[0])
        enforce_budget(histories,25000)
        assert sum(p.stat().st_size for p in tmp_path.glob('*/*.jpg'))<=25000
    restored=[PictureHistory(h.folder,count=4,age=60,budget=10000) for h in histories]
    assert sum(len(h.entries()) for h in restored)>0
    tick[0]+=61
    for h in restored:assert h.entries()==[]
    assert not list(tmp_path.glob('*/*.jpg'))

@pytest.mark.parametrize('value',[None,42,'not a list',{'wrong':'shape'}])
def test_corrupt_diagnostic_history_does_not_stop_startup_or_confidence(tmp_path,value):
    from skycam.feature_scenes import FeatureScenes
    folder=tmp_path/'broadcast';folder.mkdir()
    for name in ('source-events.json','watchdog-history.json'):
        (folder/name).write_text(json.dumps(value))
    (tmp_path/'source-health.json').write_text(json.dumps(value))
    f=FeatureScenes(tmp_path,lambda:{},{});f.collect()
    (tmp_path/'runtime'/'watchdog.json').write_text(json.dumps(value))
    status=f.confidence()
    assert status['events']==[] and status['recoveries']==[]
    assert all(not row['fresh'] for row in status['sources'])

def test_bad_source_health_fields_are_reported_unavailable(tmp_path):
    from skycam.feature_scenes import FeatureScenes
    f=FeatureScenes(tmp_path,lambda:{},{})
    for health in ({'checked_at':None,'cameras':None},{'checked_at':'oops','cameras':{'cam1':[]}}):
        (tmp_path/'source-health.json').write_text(json.dumps(health))
        f.collect()
        assert all(not row['fresh'] for row in f.confidence()['sources'])

@pytest.mark.parametrize('target,fps,level',[
    (30,30,'ok'),(30,29.5,'ok'),(30,24,'warning'),(30,40,'warning'),
    (60,60,'ok'),(60,59,'ok'),(60,30,'warning'),(30,None,'warning'),
    (30,float('nan'),'warning'),(30,'invalid','warning')])
def test_readiness_uses_configured_house_rate_and_rejects_bad_measurements(monkeypatch,target,fps,level):
    from skycam import readiness
    monkeypatch.setattr(readiness,'PROGRAM_FPS',target)
    status={'connected':True,'ready':True,'checked_at':100,'output':{'moving':True,'measured_fps':fps}}
    row=next(c for c in readiness.snapshot(status,{},{},{},{},now=101)['checks'] if c['id']=='cadence')
    assert row['level']==level
    if type(fps) in (int,float) and fps==fps:assert f'target {target}' in row['detail']
