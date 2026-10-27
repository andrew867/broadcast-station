import numpy as np
import pytest
from skycam.study_songs import compose, samples, song_info, SONG_FRAMES, PHRASE_FRAMES, RATE, BEAT
from skycam.generative_music import Generator
from skycam.music import Music, MusicConfig
from skycam import playout


@pytest.mark.parametrize('seed', [0, 247, 651836221, 2147483647])
def test_songs_have_melody_harmony_contrast_and_rest(seed):
    songs = [compose(seed, i) for i in range(4)]
    assert len({s.title for s in songs}) == 4
    assert len({s.key for s in songs}) == 4
    assert len({s.progression for s in songs}) == 4
    for song in songs:
        # Count actual lead pitches, excluding echoes and accompaniment.
        lead = [e for e in song.events if e.kind in ('felt', 'round', 'keys') and e.pan == -.12]
        assert len({e.pitch for e in lead}) >= 9
        bars = {int(e.start / RATE / BEAT / 4) for e in lead}
        assert 20 <= len(bars) <= 45  # A melody, but not a nonstop solo.
        assert not bars.intersection(range(48, 56))  # The soft interlude breathes.
        assert all(any(e.kind == 'bass' and int(e.start/RATE/BEAT/4) == bar
                       for e in song.events) for bar in range(64))
    assert compose(seed, 0) == songs[0]


@pytest.mark.parametrize('at', [PHRASE_FRAMES, SONG_FRAMES, SONG_FRAMES*2])
def test_phrase_and_song_joins_are_exact_and_audible(at):
    start = at - 2401
    audio = samples(start, 4803, 651836221)
    chunks = np.concatenate([samples(start, 1701, 651836221),
                             samples(start+1701, 3102, 651836221)])
    assert np.array_equal(audio, chunks)
    assert np.isfinite(audio).all()
    assert np.sqrt(np.mean(audio**2)) > .01
    assert abs(np.diff(audio, axis=0)).max() < .12
    assert abs(audio).max() < .68


def test_cache_revision_does_not_reuse_previous_study_audio(tmp_path):
    g = Generator(tmp_path)
    assert g.index('skygen-v2-247-study-00000004.wav', 247, 'study') is None
    assert g.index(g.name(247, 'study', 4), 247, 'study') == 4
    assert g.name(247, 'coastal', 4).startswith('skygen-v2-')
    m = Music(tmp_path)
    m.generator.folder.mkdir(parents=True)
    for version in ('v2', 'v3', 'v4'):
        name = f'skygen-{version}-247-study-00000004.wav'
        (m.generator.folder/name).touch()
        assert '/workspace/runtime/music-generator/' in m.clip(name)


def test_metadata_follows_playing_file_and_hides_unheard_new_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(playout, 'ENABLED', False)
    m = Music(tmp_path)
    m.config = MusicConfig(source='generated', mood='study', seed=247)
    m.current = m.generator.name(247, 'study', 7)
    info = m.public()['generated']['song']
    assert info['number'] == 2 and info['phrase_in_song'] == 4
    assert info['next_title'] == song_info(247, 8)['title']
    m.save(MusicConfig(source='generated', mood='study', seed=248))
    assert m.public()['generated']['song'] is None


def test_study_revision_switch_preserves_active_audio(tmp_path, monkeypatch):
    m = Music(tmp_path); m.config = MusicConfig(source='generated', mood='study')
    monkeypatch.setattr(m.generator, 'length', lambda mood: 2400)
    old = 'skygen-v2-247-study-00000084.wav'
    for i in range(3): m.generator.ensure(247, 'study', i)
    (m.generator.folder/old).touch()
    monkeypatch.setattr(playout, 'ENABLED', True)
    monkeypatch.setattr(playout, 'STATUS', {'ready': True})
    calls = []
    def command(text, **kwargs):
        calls.append(text)
        return f'<?xml version="1.0"?><channel><layer_5><foreground><file><path>{old}</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout, 'command', command)
    m.check()
    assert m.current == old and m.queued == m.generator.name(247, 'study', 0)
    assert not any(c.startswith(('PLAY ', 'CLEAR ')) for c in calls)
    assert any('LOADBG 1-5 "/workspace/runtime/music-generator/skygen-v4-' in c for c in calls)


def test_soft_interlude_has_a_continuous_musical_bed():
    # Check the complete quiet eight-bar section, not just its loud onsets.
    at = round(48*4*BEAT*48000)
    audio = samples(at, round(8*4*BEAT*48000), 651836221)
    rms = np.sqrt(np.mean(audio[:len(audio)//4800*4800].reshape(-1,4800,2)**2, axis=(1,2)))
    assert rms.min() > 10**(-50/20)
