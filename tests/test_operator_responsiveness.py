import threading
import time
import pytest
from fastapi import HTTPException
from skycam import app as api

@pytest.mark.parametrize('which',['rundown','playout'])
def test_busy_take_returns_without_waiting_or_pausing_rotation(monkeypatch,which):
    lock=threading.RLock();entered=threading.Event();release=threading.Event();calls=[]
    monkeypatch.setattr(api.rundown,'lock',lock if which=='rundown' else threading.RLock())
    monkeypatch.setattr(api.playout,'LOCK',lock if which=='playout' else threading.RLock())
    monkeypatch.setattr(api.rundown,'pause',lambda *args:calls.append('pause'))
    monkeypatch.setattr(api,'take_program',lambda *args:calls.append('take'))
    def busy():
        with lock:entered.set();release.wait(3)
    t=threading.Thread(target=busy);t.start();assert entered.wait(1)
    try:
        start=time.monotonic()
        with pytest.raises(HTTPException) as result:api.program_take('cam1')
        assert result.value.status_code==409 and time.monotonic()-start<.2
        assert calls==[]
    finally:release.set();t.join(2)

def test_unknown_scene_does_not_pause_and_valid_manual_take_is_serialized(monkeypatch):
    calls=[]
    monkeypatch.setattr(api.rundown,'pause',lambda *args:calls.append('pause'))
    monkeypatch.setattr(api,'take_program',lambda camera:calls.append(camera))
    with pytest.raises(HTTPException) as result:api.program_take('does-not-exist')
    assert result.value.status_code==404 and not calls
    api.program_take('cam1');assert calls==['pause','cam1']
