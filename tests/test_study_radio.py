import json
import numpy as np
import pytest
from skycam import study_radio as radio
from skycam.generative_music import Generator
from skycam.music import Music,MusicConfig
from skycam import playout


@pytest.mark.parametrize('seed',[0,247,651836221,2147483647])
def test_distinct_songs_and_no_empty_bars(seed):
    config=radio.canonical()
    scores=[radio.compose(seed,i,config)[0] for i in range(3)]
    assert len({radio.song_info(seed,i*4)['key'] for i in range(3)})==3
    assert len({radio.song_info(seed,i*4)['palette'] for i in range(3)})==3
    for notes in scores:
        assert 600<len(notes)<4000
        assert len({e.pitch for e in notes if e.kind not in ('bass','bed','drum')})>=12
        assert {int(e.start/radio.RATE/.75/4) for e in notes if e.kind=='bass'}==set(range(64))
        assert all(0<=e.start<radio.RATE*192 for e in notes)


@pytest.mark.parametrize('bpm',[76,80,84])
def test_wav_and_song_boundaries_are_exact(bpm):
    phrase=round(64*60/bpm*48000)
    for boundary in (phrase,phrase*4,phrase*8):
        start=boundary-2401
        whole=radio.samples(start,4803,247,{'bpm':bpm})
        split=np.concatenate([radio.samples(start,1701,247,{'bpm':bpm}),
                              radio.samples(start+1701,3102,247,{'bpm':bpm})])
        assert np.array_equal(whole,split)
        assert np.isfinite(whole).all()
        assert np.abs(whole).max()<.68
        assert np.max(np.abs(np.diff(whole,axis=0)))<.12
        assert np.sqrt(np.mean(whole**2))>.005


def test_controls_change_cache_identity_and_preserve_old_preset(tmp_path):
    original=Generator(tmp_path)
    variant=Generator(tmp_path,{'rain':.8,'bpm':84})
    assert original.name(247,'radio',0)!=variant.name(247,'radio',0)
    assert original.name(247,'strudel',0)==variant.name(247,'strudel',0)
    assert original.length('radio')==48000*48
    assert original.index(variant.name(247,'radio',0),247,'radio') is None
    assert original.index(original.name(247,'radio',42),247,'radio')==42


def test_melody_off_and_atmosphere_silent():
    notes,_=radio.compose(247,0,radio.canonical({'melody':0}))
    assert not any(e.kind in ('flute','guitar') for e in notes)
    dry=radio.samples(123456,2000,247,{'rain':0,'vinyl':0})
    wet=radio.samples(123456,2000,247,{'rain':1,'vinyl':1})
    assert not np.array_equal(dry,wet)
    assert np.max(np.abs(wet-dry))<.06


def test_volume_only_update_preserves_radio_controls(tmp_path,monkeypatch):
    monkeypatch.setattr(playout,'ENABLED',False)
    music=Music(tmp_path)
    music.save(MusicConfig(source='generated',mood='radio',radio={'rain':.8,'bpm':84}))
    music.save(MusicConfig(volume=.21))
    assert music.config.mood=='radio' and music.config.radio.rain==.8
    assert music.generator.bpm('radio')==84
    assert json.loads(music.path.read_text())['radio']['rain']==.8
    music.current=music.generator.name(247,'radio',4)
    monkeypatch.setattr(radio,'compose',lambda *a:pytest.fail('No arranger in status request'))
    assert music.public()['generated']['song']['number']==2
