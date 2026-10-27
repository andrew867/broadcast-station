import pytest
from skycam import playout
from skycam.music import Music


@pytest.mark.parametrize('shuffle,expected',[(True,'c.wav'),(False,'a.wav')])
def test_startup_honours_shuffle_before_playing(tmp_path,monkeypatch,shuffle,expected):
    for name in ['a.wav','b.wav','c.wav']:(tmp_path/name).touch()
    music=Music(tmp_path);music.folder=tmp_path;music.config.shuffle=shuffle
    calls=[]
    monkeypatch.setattr(playout,'ENABLED',True)
    monkeypatch.setattr(playout,'STATUS',{'ready':True})
    monkeypatch.setattr(playout,'CAMERA_AUDIO',False)
    monkeypatch.setattr('skycam.music.random.choice',lambda choices:choices[-1])
    def command(text,**kwargs):
        calls.append(text)
        return '<?xml version="1.0"?><channel />'
    monkeypatch.setattr(playout,'command',command)
    music.check()
    assert music.error is None
    assert music.current==expected
    assert [c for c in calls if c.startswith('PLAY ')]==[f'PLAY 1-5 "/workspace/media/music/{expected}"']
    assert music.queued!=music.current


def test_controller_restart_adopts_playing_track_without_restarting_it(tmp_path,monkeypatch):
    for name in ['a.wav','b.wav','c.wav']:(tmp_path/name).touch()
    music=Music(tmp_path);music.folder=tmp_path;music.config.shuffle=True
    calls=[]
    monkeypatch.setattr(playout,'ENABLED',True)
    monkeypatch.setattr(playout,'STATUS',{'ready':True})
    monkeypatch.setattr(playout,'CAMERA_AUDIO',False)
    def command(text,**kwargs):
        calls.append(text)
        return '<?xml version="1.0"?><channel><layer_5><foreground><file><path>/workspace/media/music/b.wav</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command)
    music.check()
    assert music.current=='b.wav'
    assert not any(c.startswith('PLAY ') for c in calls)


@pytest.mark.parametrize('names,expected',[([],None),(['only.wav'],'only.wav')])
def test_shuffle_handles_empty_and_single_track_folders(tmp_path,monkeypatch,names,expected):
    for name in names:(tmp_path/name).touch()
    music=Music(tmp_path);music.folder=tmp_path;music.config.shuffle=True
    monkeypatch.setattr(playout,'ENABLED',True)
    monkeypatch.setattr(playout,'STATUS',{'ready':True})
    monkeypatch.setattr(playout,'CAMERA_AUDIO',False)
    monkeypatch.setattr(playout,'command',lambda *args,**kwargs:'<?xml version="1.0"?><channel />')
    music.check()
    assert music.current==expected
    assert music.error is None
