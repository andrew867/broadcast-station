import wave
import numpy as np
import pytest
from skycam.generative_music import Generator,RATE,samples
from skycam.music import Music,MusicConfig
from skycam import playout

@pytest.mark.parametrize('mood',['coastal','night','lofi','study'])
def test_sample_blocks_are_continuous_and_bounded(mood):
    start=RATE*48-1200
    whole=samples(start,2400,247,mood)
    blocks=np.concatenate((samples(start,1200,247,mood),samples(start+1200,1200,247,mood)))
    assert np.array_equal(whole,blocks)
    assert np.isfinite(whole).all() and abs(whole).max()<.68
    assert np.sqrt(np.mean(whole**2))>.005
    assert abs(np.diff(whole,axis=0)).max()<.12
    assert not np.array_equal(whole,samples(start,2400,248,mood))

def test_render_wav_and_cache_pruning(tmp_path,monkeypatch):
    g=Generator(tmp_path);monkeypatch.setattr(g,'length',lambda mood:2400)
    names=[g.ensure(247,'coastal',i) for i in range(4)]
    with wave.open(str(tmp_path/names[0])) as f:
        assert (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())==(2,2,48000,2400)
    g.prune(set(names[1:]));assert len(list(tmp_path.glob('*.wav')))==3
    assert not list(tmp_path.glob('*.tmp'))

def test_generated_mode_queues_sequential_phrases_and_adopts_on_reload(tmp_path,monkeypatch):
    m=Music(tmp_path);m.config=MusicConfig(source='generated',shuffle=True)
    monkeypatch.setattr(m.generator,'length',lambda mood:2400)
    current=m.generator.ensure(247,'coastal',5)
    m.generator.ensure(247,'coastal',6);m.generator.ensure(247,'coastal',7)
    monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    calls=[]
    def command(text,**kwargs):
        calls.append(text)
        return f'<?xml version="1.0"?><channel><layer_5><foreground><file><path>/workspace/runtime/music-generator/{current}</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command)
    m.check()
    assert not m.error and m.current==current
    assert not any(c.startswith('PLAY ') for c in calls)
    assert m.queued.endswith('00000006.wav')
    assert len(list(m.generator.folder.glob('*.wav')))==3
    assert any(c.startswith('LOADBG 1-5 "/workspace/runtime/music-generator/') for c in calls)

def test_legacy_volume_update_preserves_source(tmp_path,monkeypatch):
    monkeypatch.setattr(playout,'ENABLED',False)
    m=Music(tmp_path);m.config=MusicConfig(source='generated',mood='night',seed=99)
    m.save(MusicConfig(volume=.23))
    assert (m.config.source,m.config.mood,m.config.seed,m.config.volume)==('generated','night',99,.23)

def test_failed_generation_does_not_clear_playing_bus(tmp_path,monkeypatch):
    m=Music(tmp_path);m.config=MusicConfig(source='generated')
    name=m.generator.name(247,'coastal',4);m.generator.folder.mkdir(parents=True);(m.generator.folder/name).touch();m.current=name
    monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    calls=[]
    def command(text,**kwargs):
        calls.append(text)
        return f'<?xml version="1.0"?><channel><layer_5><foreground><file><path>{name}</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command)
    def fail(*args):raise OSError('test disk unavailable')
    monkeypatch.setattr('skycam.music.render_phrase',fail);m.check()
    try:m.render_job.result(timeout=3)
    except OSError:pass
    m.check()
    assert m.error=='Local service or file operation failed'
    assert any('LOOP AUTO' in c for c in calls)
    assert not any(c.startswith('CLEAR') for c in calls)


def test_seed_change_waits_for_phrase_boundary(tmp_path,monkeypatch):
    m=Music(tmp_path);m.config=MusicConfig(source='generated',mood='lofi',seed=999)
    monkeypatch.setattr(m.generator,'length',lambda mood:2400)
    old=m.generator.ensure(247,'coastal',5)
    for i in range(3):m.generator.ensure(999,'lofi',i)
    monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    calls=[]
    def command(text,**kwargs):
        calls.append(text)
        return f'<?xml version="1.0"?><channel><layer_5><foreground><file><path>{old}</path></file></foreground></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command);m.check()
    assert m.current==old and m.queued==m.generator.name(999,'lofi',0)
    assert any(c.startswith('LOADBG ') for c in calls)
    assert not any(c.startswith(('PLAY ','CLEAR ')) for c in calls)


def test_lofi_phrase_boundaries_and_variation():
    from skycam.lofi_music import variation,BPM
    assert len(set(int(variation(247,i)) for i in range(100)))==100
    for section in range(1,6):
        at=round(section*8*4*60/BPM*RATE)
        sound=samples(at-1200,2400,247,'lofi')
        assert abs(np.diff(sound,axis=0)).max()<.12
        assert np.sqrt(np.mean(sound**2))>.01


@pytest.mark.parametrize('bpm,mood',[(78,'lofi'),(74,'study')])
def test_groove_at_many_pattern_and_phrase_boundaries(bpm,mood):
    for i in range(1,7):
        at=round(i*32*60/bpm*RATE)
        a=samples(at-2400,4800,651836221,mood)
        assert np.isfinite(a).all() and abs(np.diff(a,axis=0)).max()<.12
        assert np.sqrt(np.mean(a*a))>.01
