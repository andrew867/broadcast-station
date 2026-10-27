import subprocess
import wave

import pytest
from skycam import playout, music_worker
from skycam.generative_music import Generator
from skycam.music import Music, MusicConfig


def test_worker_timeout_removes_partial_output_and_bounds_process(tmp_path, monkeypatch):
    generator=Generator(tmp_path)
    name=generator.name(247,'coastal',1)
    def timeout(args, **kwargs):
        assert kwargs['timeout']==90 and kwargs['env']['OPENBLAS_NUM_THREADS']=='1'
        assert kwargs['stdout']==subprocess.DEVNULL and kwargs['stderr']==subprocess.DEVNULL
        assert args[1:3]==['-m','skycam.music_worker']
        (tmp_path/name).with_suffix('.tmp').write_bytes(b'incomplete')
        raise subprocess.TimeoutExpired(args,90)
    monkeypatch.setattr(music_worker.subprocess,'run',timeout)
    with pytest.raises(subprocess.TimeoutExpired):music_worker.render(generator,247,'coastal',1)
    assert not list(tmp_path.iterdir())


def test_worker_rejects_incomplete_audio_even_after_successful_exit(tmp_path,monkeypatch):
    generator=Generator(tmp_path)
    def render(args,**kwargs):
        with wave.open(str(tmp_path/generator.name(247,'coastal',1)),'wb') as wav:
            wav.setparams((2,2,48000,0,'NONE','not compressed'));wav.writeframes(b'\0'*400)
        return subprocess.CompletedProcess(args,0)
    monkeypatch.setattr(music_worker.subprocess,'run',render)
    with pytest.raises(ValueError,match='incomplete'):music_worker.render(generator,247,'coastal',1)
    assert not list(tmp_path.iterdir())


def test_real_isolated_phrase_is_valid_and_reused(tmp_path,monkeypatch):
    generator=Generator(tmp_path)
    name=music_worker.render(generator,247,'coastal',0)
    with wave.open(str(tmp_path/name)) as wav:
        assert wav.getnframes()==generator.length('coastal')
    assert generator.last_render_seconds>0
    monkeypatch.setattr(music_worker.subprocess,'run',lambda *a,**kw:pytest.fail('Should reuse complete phrase'))
    assert music_worker.render(generator,247,'coastal',0)==name


def test_crossfade_uses_output_clock_and_never_overlaps_generated_phrases(tmp_path):
    music=Music(tmp_path)
    music.config=MusicConfig(crossfade_seconds=2.5)
    assert music.transition()==f' MIX {playout.transition_frames(150)} LINEAR'
    music.config.source='generated'
    assert music.transition()==''


def test_old_clients_cannot_reset_crossfade(tmp_path,monkeypatch):
    monkeypatch.setattr(playout,'ENABLED',False)
    music=Music(tmp_path);music.config.crossfade_seconds=2
    music.save(MusicConfig(volume=.1))
    assert music.config.crossfade_seconds==2


def test_pending_generation_supplies_fallback_only_when_background_empty(tmp_path,monkeypatch):
    import xml.etree.ElementTree as ET
    music=Music(tmp_path);music.generator.folder.mkdir(parents=True)
    (music.generator.folder/'phrase.wav').touch()
    calls=[]
    monkeypatch.setattr(playout,'command',lambda text,**kw:calls.append(text))
    music.hold_phrase('phrase.wav',ET.fromstring('<channel/>'))
    assert calls[-1].endswith(' LOOP AUTO')
    music.hold_phrase('phrase.wav',ET.fromstring('<channel><layer_5><background><producer>ffmpeg</producer></background></layer_5></channel>'))
    assert len(calls)==1


def test_finished_render_replaces_temporary_loop(tmp_path,monkeypatch):
    music=Music(tmp_path);music.config=MusicConfig(source='generated')
    monkeypatch.setattr(music.generator,'length',lambda mood:2400)
    names=[music.generator.ensure(247,'coastal',i) for i in range(3)]
    music.current=music.queued=names[0];music.fallback_queued=True
    monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    calls=[]
    def command(text,**kwargs):
        calls.append(text)
        return f'<?xml version="1.0"?><channel><layer_5><foreground><file><path>{names[0]}</path></file></foreground><background><producer>ffmpeg</producer></background></layer_5></channel>'
    monkeypatch.setattr(playout,'command',command)
    music.check()
    assert music.queued==names[1] and not music.fallback_queued
    assert any(names[1] in call and call.endswith(' AUTO') for call in calls)
    queue=next(i for i,c in enumerate(calls) if names[1] in c and c.startswith('LOADBG '))
    assert calls[queue+1]=='CALL 1-5 LOOP 0'


def test_quiet_gain_applies_even_during_generator_retry_backoff(tmp_path,monkeypatch):
    import time
    music=Music(tmp_path);music.config=MusicConfig(source='generated')
    music.retry_at=time.monotonic()+30;music.last_gain=.18
    monkeypatch.setattr(music,'effective_volume',lambda:.08)
    monkeypatch.setattr(playout,'ENABLED',True);monkeypatch.setattr(playout,'STATUS',{'ready':True})
    calls=[]
    def command(text,**kwargs):
        calls.append(text);return '<?xml version="1.0"?><channel/>'
    monkeypatch.setattr(playout,'command',command)
    music.check()
    assert music.last_gain==.08
    assert any(c.startswith('MIXER 1-5 VOLUME 0.08 ') for c in calls)
    assert not any(c.startswith(('PLAY ','CLEAR ')) for c in calls)


def test_restart_releases_native_fallback_loop_without_python_flag(tmp_path,monkeypatch):
    music=Music(tmp_path);music.config=MusicConfig(source='generated')
    calls=[];monkeypatch.setattr(playout,'command',calls.append)
    music.queue_next('skygen-v2-247-coastal-00000001.wav')
    assert calls[0].startswith('LOADBG ') and calls[1]=='CALL 1-5 LOOP 0'
    music.config.source='playlist';calls.clear();music.queue_next('disk.wav')
    assert len(calls)==1 and calls[0].endswith(' AUTO')
