from datetime import datetime,timedelta,timezone
import pytest
from skycam.notices import Notice,NoticeWrite,NoticeBoard
from skycam.rundown_library import LibraryConflict
from skycam.community_cards import notice_pages,notice_image

def test_approval_dates_expiry_and_revision(tmp_path):
    now=datetime.now(timezone.utc);board=NoticeBoard(tmp_path)
    n=Notice(title='Community test',text='This is an off-air test.',starts_at=now,ends_at=now+timedelta(hours=1))
    board.save(NoticeWrite(expected_revision=0,notice=n));assert not board.public(now)['items'][0]['active']
    n.approved=True;board.save(NoticeWrite(expected_revision=1,notice=n))
    assert board.public(now)['items'][0]['active']
    assert not board.public(now-timedelta(seconds=1))['items'][0]['active']
    assert not board.public(n.ends_at)['items'][0]['active']
    with pytest.raises(LibraryConflict):board.delete(n.id,0)
    restored=NoticeBoard(tmp_path);assert restored.revision==2
    restored.delete(n.id,2);assert not restored.public()['items']
    with pytest.raises(ValueError):Notice(title=' ',text='Message')
    with pytest.raises(ValueError):Notice(title='Test',text='Message',ends_at=datetime(2026,1,1))
    with pytest.raises(ValueError):Notice(title='Test',text='Message',starts_at=now,ends_at=now)

def test_notice_paging_retains_text_and_no_bad_cache(tmp_path):
    text=' '.join('word'+str(i) for i in range(180))
    n=Notice(title='Long notice',text=text)
    rows=notice_pages([n.model_dump(mode='json')])
    assert len(rows)>1
    assert ' '.join(line for row in rows for line in row['lines'])==text
    for row in rows:assert notice_image(row).size==(3840,2160)
    board=NoticeBoard(tmp_path);board.path.parent.mkdir(parents=True);board.path.write_text('broken')
    damaged=NoticeBoard(tmp_path);assert damaged.error and damaged.active()==[]
    with pytest.raises(RuntimeError):damaged.save(NoticeWrite(expected_revision=0,notice=n))

def test_notice_preview_does_not_save_or_air(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module
    # Test operator authorization in memory; network and playout remain disabled.
    monkeypatch.setattr(module,'preview_read_only',lambda:False)
    monkeypatch.setattr(module,'notices',NoticeBoard(tmp_path));client=TestClient(module.app)
    response=client.post('/api/notices/preview',headers={'X-Skycam-Edit':'1'},json={'title':'Off-air draft','text':'Preview only'})
    assert response.status_code==200 and response.headers['content-type']=='image/png'
    assert not module.notices.public()['items'] and not module.notices.path.exists()
