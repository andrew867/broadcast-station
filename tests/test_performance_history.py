import json
from skycam.performance_history import PerformanceHistory


def sample(at,fps=30,scene='quad'):
    return {'at':at,'fps':fps,'scene':scene,'sources':{'cam1':{'display':'loading'}},
            'transition':{'at':at,'fallback_cut':True},'memory':{'available_bytes':4000},'graphics':{'device_bytes':800}}


def test_minute_history_survives_restart_and_keeps_missing_gaps(tmp_path):
    h=PerformanceHistory(tmp_path,now=120)
    h.add(sample(120));h.add(sample(125,None));h.add(sample(130,24));h.add(sample(300))
    restored=PerformanceHistory(tmp_path,now=305).public(305)
    assert len(restored['minutes'])==1
    assert restored['summary']['average_fps']==27 and restored['summary']['missing_samples']==1
    assert restored['minutes'][0]['source_unavailable']=={'cam1':3}
    assert h.public(305)['summary']['minutes_observed']==2
    assert len(list(tmp_path.glob('*.jsonl')))==1


def test_history_bounds_retention_and_ignores_corrupt_files(tmp_path):
    h=PerformanceHistory(tmp_path,now=0)
    for t in range(0,90001,60):h.add(sample(t))
    assert len(h.public(90000)['minutes'])<=1441 and len(list(tmp_path.glob('hour-*.jsonl')))<=25
    (tmp_path/'hour-25.jsonl').write_text('invalid\n{}\n'+json.dumps({'at':90001,'samples':0})+'\n')
    reloaded=PerformanceHistory(tmp_path,now=90030)
    assert reloaded.public(90030)['summary']['average_fps']==30


def test_history_deduplicates_transitions_and_handles_clock_backwards(tmp_path):
    h=PerformanceHistory(tmp_path,now=1000);s=sample(1020)
    h.add(s);h.add({**s,'at':1025});h.add(sample(1000))
    result=h.public(1030);assert result['summary']['transitions']==1
    assert result['minutes'][0]['samples']==2
    result['minutes'][0]['samples']=99
    assert h.public(1030)['minutes'][0]['samples']==2


def test_disk_failure_does_not_discard_live_history(tmp_path,monkeypatch):
    h=PerformanceHistory(tmp_path,now=120);h.add(sample(120))
    from pathlib import Path
    original=Path.open
    def fail(self,*args,**kwargs):
        if args and args[0]=='a':raise OSError('disk unavailable')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',fail)
    h.add(sample(180))
    assert h.public(185)['summary']['minutes_observed']==2 and h.public(185)['error']
