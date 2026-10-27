import threading
import time
from skycam.rundown import Rundown
from skycam.performance import Performance


def test_status_does_not_wait_for_preparation_or_expose_partial_edit(tmp_path):
    r=Rundown(tmp_path,lambda *a:None);entered=threading.Event();release=threading.Event()
    def edit():
        with r._editing():
            r.index=2;entered.set();release.wait(3)
    t=threading.Thread(target=edit);t.start();assert entered.wait(1)
    try:
        start=time.monotonic();snapshot=r.public()
        assert time.monotonic()-start<.2
        assert snapshot['busy'] and snapshot['index']==0
        snapshot['cues'].clear()
        assert r.public()['cues']
    finally:release.set();t.join(2)
    assert not r.public()['busy'] and r.public()['index']==2


def test_performance_bounds_gaps_and_deduplicates_transitions():
    p=Performance(3)
    status={'checked_at':100,'output':{'measured_fps':40,'frames':200,'moving':True},
            'transition':{'at':95,'fallback_cut':True},'cameras':{}}
    for at in (100,101,102,110):p.sample(status,now=at)
    result=p.public();s=result['summary']
    assert s['samples']==3 and s['valid_samples']==2 and s['stale_samples']==1
    assert s['average_fps']==40 and s['fallback_cuts']==1 and s['transitions']==1
    assert result['samples'][-1]['fps'] is None and not result['samples'][-1]['moving']
    result['samples'].clear();assert len(p.public()['samples'])==3


def test_missing_and_invalid_metrics_are_not_zero_fps():
    p=Performance();p.sample({},now=100)
    p.sample({'checked_at':100,'output':{'measured_fps':float('nan')}},now=100)
    assert p.public()['summary']['average_fps'] is None
