import hashlib,json,math,shutil,wave
import numpy as np
import pytest
from skycam.music_levels import LevelLibrary,gain_for,fingerprint,prepare
from skycam.music import Music,MusicConfig
from skycam import playout


def library(tmp_path):
    original=tmp_path/'Song.wav';original.write_bytes(b'original')
    lib=LevelLibrary(tmp_path);lib.cache.mkdir()
    output='level-'+'a'*24+'.wav';(lib.cache/output).write_bytes(b'prepared')
    lib.rows={'Song.wav':{'source_stat':fingerprint(original),'output':output,'output_size':8,'verified':True}}
    (lib.cache/'manifest.json').write_text(json.dumps({'schema':1,'tracks':lib.rows}))
    return lib,output


def test_constant_gain_respects_peak_and_boost_limit():
    assert gain_for(-17,-1)==-9
    assert gain_for(-40,-30)==12
    assert gain_for(-30,-2)==-1
    with pytest.raises(ValueError):gain_for(float('-inf'),float('-inf'))


def test_original_changes_invalidate_prepared_copy_and_bad_cache_fails_closed(tmp_path):
    lib,output=library(tmp_path);lib.refresh();assert lib.ready('Song.wav')==output
    assert lib.original(output)=='Song.wav'
    (tmp_path/'Song.wav').write_bytes(b'new original')
    assert lib.ready('Song.wav') is None
    (lib.cache/'manifest.json').write_text('{broken');lib.refresh();assert lib.rows=={}


def test_controller_adopts_prepared_file_and_preserves_original_names(tmp_path,monkeypatch):
    lib,output=library(tmp_path)
    music=Music(tmp_path);music.folder=tmp_path;music.config.match_levels=True
    monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    calls=[]
    def command(text,**kwargs):
        calls.append(text)
        return f'<?xml version="1.0"?><channel><layer_5><foreground><file><path>/workspace/media/music/.skycam-levels/{output}</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command)
    music.check()
    assert music.current=='Song.wav' and music.error is None
    assert not any(c.startswith('PLAY ') for c in calls)
    assert '.skycam-levels/' in next(c for c in calls if c.startswith('LOADBG '))
    assert music.public()['files']==['Song.wav']
    music.save(MusicConfig(volume=.1));assert music.config.match_levels


def test_missing_prepared_library_cannot_be_enabled(tmp_path,monkeypatch):
    monkeypatch.setattr(playout,'ENABLED',False)
    music=Music(tmp_path);music.folder=tmp_path
    with pytest.raises(ValueError,match='Prepare'):music.save(MusicConfig(match_levels=True))
    assert not music.config.match_levels


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg required for real preparation')
def test_full_track_preparation_verifies_audio_and_preserves_original(tmp_path):
    source=tmp_path/'tone.wav'
    values=(np.sin(np.arange(48000*4)*2*math.pi*440/48000)*14000).astype('<i2')
    with wave.open(str(source),'wb') as w:
        w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(values.tobytes())
    before=hashlib.sha256(source.read_bytes()).hexdigest();lib=LevelLibrary(tmp_path)
    row=prepare(source,lib)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    assert abs(row['output_lufs']+26)<.2 and row['output_peak_dbtp']<=-3
    lib.refresh();assert lib.ready(source.name)==row['output']
