from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from skycam.dayparts import Dayparts,DaypartConfig,DaypartWrite
from skycam.rundown import Rundown,RundownConfig,Cue
from skycam.music import Music,MusicConfig

ID='a'*32
def stamp(local):return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo('America/St_Johns')).timestamp()
def config(**kw):return DaypartConfig(enabled=True,periods=[{'name':'Night','playlist_id':ID,'start':'22:00','end':'07:00'}],**kw)
def library(_):return {'name':'Night loop','config':RundownConfig(cues=[Cue(camera='map')]).model_dump()}


def test_windows_midnight_dst_and_validation(tmp_path):
    d=Dayparts(tmp_path,library);d.save(DaypartWrite(expected_revision=0,config=config()))
    for local in ('2026-10-18T23:00','2026-10-19T02:00','2026-11-01T01:30'):
        assert d.selection(stamp(local))['name']=='Night'
    assert d.selection(stamp('2026-10-19T07:00')) is None
    with pytest.raises(ValueError):
        DaypartConfig(periods=[{'name':'bad','playlist_id':ID,'start':'24:00','end':'07:00'}])
    with pytest.raises(ValueError):
        DaypartConfig(periods=[*config().periods,{'name':'Overlap','playlist_id':ID,'start':'06:00','end':'09:00'}])
    with pytest.raises(ValueError):d.save(DaypartWrite(expected_revision=0,config=config()))
    assert Dayparts(tmp_path,library).config==d.config


def test_manual_hold_boundary_and_saved_loop_preserved(tmp_path):
    takes=[];r=Rundown(tmp_path,lambda *args:takes.append(args))
    r.save(RundownConfig(cues=[Cue(camera='cam1'),Cue(camera='cam2')]))
    saved=r.path.read_bytes()
    class Selector:
        def __init__(self):self.selected=None
        def selection(self):return self.selected
    d=Selector();r.dayparts=d;r.action('start')
    d.selected={'key':'night','name':'Night','config':library(ID)['config']}
    r.advance_due();assert takes[-1][0]=='cam1'
    r.deadline=0;r.advance_due();assert takes[-1][0]=='map'
    assert r.public()['daypart']['name']=='Night' and r.path.read_bytes()==saved
    r.pause();count=len(takes);r.advance_due();assert len(takes)==count
    r.action('start');assert takes[-1][0]=='map'
    d.selected=None;r.deadline=0;r.advance_due();assert takes[-1][0]=='cam1'
    assert r.public()['daypart'] is None and r.path.read_bytes()==saved


def test_block_finishes_before_daypart_change(tmp_path):
    takes=[];r=Rundown(tmp_path,lambda *args:takes.append(args))
    class Selector:
        def selection(self):return {'key':'night','name':'Night','config':library(ID)['config']}
    r.action('start');r._start_block({'name':'Forecast','config':RundownConfig(cues=[Cue(camera='weather')]).model_dump(),'include_alerts':False,'rule_id':'test','scheduled_at':0})
    r.dayparts=Selector();r.advance_due();assert takes[-1][0]=='weather'
    r.deadline=0;r.advance_due();assert takes[-1][0]=='map' and r.block is None


def test_quiet_volume_ceiling_and_alert_restore(tmp_path,monkeypatch):
    from skycam import playout
    monkeypatch.setattr(playout,'ENABLED',False)
    m=Music(tmp_path);m.save(MusicConfig(quiet_enabled=True,volume=.2,quiet_volume=.08))
    night=stamp('2026-10-18T23:00');day=stamp('2026-10-19T12:00')
    assert m.effective_volume(night)==.08 and m.effective_volume(day)==.2
    m.ducked=True;assert m.effective_volume(night)==0
    m.ducked=False;m.save(MusicConfig(volume=.04))
    assert m.config.quiet_enabled and m.effective_volume(night)==.04
