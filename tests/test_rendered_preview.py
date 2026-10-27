import json
import pytest
from PIL import Image
from skycam.rendered_preview import RenderedPreview,SnapshotBusy
from skycam import playout

def setup(monkeypatch,tmp_path):
    item=RenderedPreview(tmp_path)
    monkeypatch.setattr(playout,'ENABLED',True)
    monkeypatch.setattr(playout,'STATUS',{'ready':True})
    monkeypatch.setattr(playout,'_camera','cam1');monkeypatch.setattr(playout,'_bank',2)
    monkeypatch.setattr(playout,'_prepared',{'bank':3,'camera':'map','at':15})
    calls=[]
    def command(text):
        calls.append(text);name=json.loads(text.split(' ',2)[2]).split('/')[-1]
        Image.new('RGB',(1920,1080),'red').save(item.folder/(name+'.png'))
        return '202 PRINT OK'
    monkeypatch.setattr(playout,'command',command)
    return item,calls

def test_native_capture_is_bounded_and_does_not_take(monkeypatch,tmp_path):
    item,calls=setup(monkeypatch,tmp_path)
    result=item.capture('preview')
    assert result['scene']=='map' and result['channel']==3 and calls[0].startswith('PRINT 3 ')
    assert len(calls)==1
    with Image.open(item.file(result['url'].split('/')[-1])) as im:assert im.size==(1280,720)
    assert not list(item.folder.glob('raw-*'))
    with pytest.raises(SnapshotBusy,match='ten seconds'):item.capture('program')
    with pytest.raises(ValueError):item.file('../../etc/passwd')

def test_no_prepared_or_reused_bank_never_mislabels(monkeypatch,tmp_path):
    item,calls=setup(monkeypatch,tmp_path)
    monkeypatch.setattr(playout,'_prepared',None)
    with pytest.raises(SnapshotBusy,match='No scene'):item.capture('preview')
    assert not calls
    original=playout.command
    def changed(text):
        original(text);playout._camera='cam2'
    monkeypatch.setattr(playout,'command',changed)
    with pytest.raises(SnapshotBusy,match='Scene changed'):item.capture('program')
    assert not list(item.folder.glob('*.jpg'))


def test_late_abandoned_prints_are_removed_without_deleting_recent_files(monkeypatch,tmp_path):
    import os,time
    item,calls=setup(monkeypatch,tmp_path)
    old=item.folder/('raw-'+'a'*32+'.png');old.write_bytes(b'late print')
    recent=item.folder/('raw-'+'b'*32+'.png');recent.write_bytes(b'pending')
    other=item.folder/'operator.png';other.write_bytes(b'keep')
    os.utime(old,(time.time()-60,time.time()-60))
    item.capture('program')
    assert not old.exists() and recent.exists() and other.exists()


def test_brief_health_poll_does_not_reject_operator_still(monkeypatch,tmp_path):
    import threading,time
    item,calls=setup(monkeypatch,tmp_path)
    lock=threading.RLock();monkeypatch.setattr(playout,'LOCK',lock)
    acquired=threading.Event()
    def health_poll():
        with lock:
            acquired.set();time.sleep(.1)
    worker=threading.Thread(target=health_poll);worker.start()
    assert acquired.wait(1)
    try:assert item.capture('program')['scene']=='cam1'
    finally:worker.join(2)
    assert len(calls)==1
