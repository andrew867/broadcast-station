import numpy as np
import pytest
from skycam.strudel_music import compose, samples, song_info
from skycam.study_songs import PHRASE_FRAMES, SONG_FRAMES
from skycam.music import Music, MusicConfig
from skycam.generative_music import Generator
from skycam import playout

@pytest.mark.parametrize('seed',[0,247,651836221,2147483647])
def test_real_strudel_arrangements_have_distinct_songs_and_full_accompaniment(seed):
    scores=[compose(seed,i) for i in range(3)]
    assert len({s.key for s in scores})==3
    assert len({s.title for s in scores})==3
    for score in scores:
        assert 1000<len(score.events)<6000
        assert len({n.pitch for n in score.events if n.kind not in ('drum','roundbass','warmbed')})>=12
        assert {int(n.start/24000/(60/74)/4) for n in score.events if n.kind=='roundbass'}==set(range(64))
    assert len({song_info(seed,i*4)['palette'] for i in range(3)})==3

@pytest.mark.parametrize('at',[PHRASE_FRAMES,SONG_FRAMES,SONG_FRAMES*2])
def test_independent_wav_blocks_and_song_tails_join_exactly(at):
    start=at-2401
    full=samples(start,4803,247)
    split=np.concatenate([samples(start,1701,247),samples(start+1701,3102,247)])
    assert np.array_equal(full,split)
    assert np.isfinite(full).all()
    assert np.sqrt(np.mean(full**2))>.01
    assert np.abs(np.diff(full,axis=0)).max()<.12
    assert np.abs(full).max()<.68

def test_status_is_fast_and_does_not_launch_arranger(tmp_path,monkeypatch):
    monkeypatch.setattr(playout,'ENABLED',False)
    m=Music(tmp_path);m.config=MusicConfig(source='generated',mood='strudel')
    m.current=m.generator.name(247,'strudel',7)
    import skycam.strudel_music as module
    monkeypatch.setattr(module,'compose',lambda *args:pytest.fail('No process on request path'))
    song=m.public()['generated']['song']
    assert song['number']==2 and song['phrase_in_song']==4
    assert song['engine'].startswith('Strudel')
    assert m.transition()==''

def test_failed_arranger_never_publishes_partial_phrase(tmp_path,monkeypatch):
    import skycam.strudel_music as module
    module.compose.cache_clear()
    def failed(*args,**kwargs):raise FileNotFoundError('node unavailable')
    monkeypatch.setattr(module.subprocess,'run',failed)
    generator=Generator(tmp_path)
    with pytest.raises(FileNotFoundError):generator.ensure(248,'strudel',0)
    assert not list(tmp_path.glob('*.wav')) and not list(tmp_path.glob('*.tmp'))
