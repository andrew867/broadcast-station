from .public_errors import public_error
from .station_config import CONFIG
"""Local music folder playout on a dedicated CasparCG audio layer."""
import asyncio,json,os,threading,random,time
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from . import playout
from .models import StrictModel
from pydantic import Field
from typing import Literal
from .generative_music import Generator,MOODS
from .music_worker import render as render_phrase
from concurrent.futures import ThreadPoolExecutor
from .music_levels import LevelLibrary,TARGET
from .study_radio_config import StudyRadioConfig
from .music_status import split_status

class MusicConfig(StrictModel):
    source:Literal['playlist','generated']='playlist'
    mood:Literal['coastal','night','lofi','study','warm','strudel','radio']='coastal'
    radio:StudyRadioConfig=Field(default_factory=StudyRadioConfig)
    seed:int=Field(default=247,ge=0,le=2147483647)
    shuffle:bool=False
    enabled:bool=True
    volume:float=Field(default=.18,ge=0,le=1)
    quiet_enabled:bool=False
    quiet_start:str=Field(default='22:00',pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    quiet_end:str=Field(default='07:00',pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    quiet_volume:float=Field(default=.08,ge=0,le=1)
    crossfade_seconds:float=Field(default=0,ge=0,le=5)
    match_levels:bool=False

class Music:
    def __init__(self,data):
        self.path=data/'broadcast'/'music.json';self.folder=Path(os.environ.get('SKYCAM_MUSIC','/music'))
        self.config=MusicConfig.model_validate_json(self.path.read_text(encoding='utf-8')) if self.path.exists() else MusicConfig()
        self.ducked=False;self.lock=threading.RLock();self.current=None;self.queued=None;self.files=[];self.error=None;self.history=[];self.pending=None
        self.last_gain=None
        self.fallback_queued=False
        self.levels=LevelLibrary(self.folder)
        self.generator=Generator(data/'runtime'/'music-generator',self.config.radio.model_dump());self.disk_files=[];self.retry_at=0
        self.render_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='skycam-music');self.render_job=None
    def public(self):
        with self.lock:
            error,note=split_status(self.error)
            self.levels.folder=self.folder;self.levels.cache=self.folder/'.skycam-levels';self.levels.refresh()
            ready=[name for name in self.disk_files if self.levels.ready(name)]
            index=self.generator.index(self.current,self.config.seed,self.config.mood)
            song=None
            if self.config.mood in ('study','warm') and index is not None:
                from .study_songs import song_info
                song=song_info(self.config.seed,index,warm=self.config.mood=='warm')
            if self.config.mood=='radio' and index is not None:
                from .study_radio import song_info as radio_info
                song=radio_info(self.config.seed,index,self.config.radio.model_dump())
            if self.config.mood=='strudel' and index is not None:
                from .strudel_music import song_info as strudel_info
                song=strudel_info(self.config.seed,index)
            return {**self.config.model_dump(),'level_matching':{'prepared':len(ready),'total':len(self.disk_files),'target_lufs':TARGET,'active':self.config.source=='playlist' and self.config.match_levels},'effective_volume':self.effective_volume(),'quiet_active':self.quiet_active(),'current':self.current,'next':self.queued,'files':ready if self.config.source=='playlist' and self.config.match_levels else self.disk_files,'error':error,'note':note,'folder':str(self.folder),'generated':{'name':MOODS[self.config.mood]['name'],'bpm':self.generator.bpm(self.config.mood),'render_seconds':self.generator.last_render_seconds,'phrase_seconds':self.generator.length(self.config.mood)/48000,'buffered_phrases':len(list(self.generator.folder.glob('*.wav'))),'variation':index,'song':song,'evolving':self.config.mood in ('lofi','study','warm','strudel','radio')}}
    def quiet_active(self,now=None):
        from .dayparts import minute,contains
        local=datetime.fromtimestamp(time.time() if now is None else now,ZoneInfo(CONFIG.location.timezone))
        return (self.config.quiet_enabled and self.config.quiet_start!=self.config.quiet_end and
                contains(minute(self.config.quiet_start),minute(self.config.quiet_end),local.hour*60+local.minute))
    def effective_volume(self,now=None):
        if self.ducked:return 0
        return min(self.config.volume,self.config.quiet_volume) if self.quiet_active(now) else self.config.volume
    def save(self,config):
        with self.lock:
            # Old desk clients changing volume must not silently select playlist.
            config=config.model_copy(update={k:getattr(self.config,k) for k in ('source','mood','seed','quiet_enabled','quiet_start','quiet_end','quiet_volume','crossfade_seconds','match_levels','radio') if k not in config.model_fields_set})
            if config.source=='playlist' and config.match_levels:
                self.levels.folder=self.folder;self.levels.cache=self.folder/'.skycam-levels';self.levels.refresh()
                if not any(self.levels.ready(p.name) for p in self.folder.glob('*') if p.is_file()):
                    raise ValueError('Prepare at least one level-matched track before enabling this playlist')
            shuffle_changed=any(getattr(config,k)!=getattr(self.config,k) for k in ('shuffle','crossfade_seconds','match_levels'))
            source_changed=any(getattr(config,k)!=getattr(self.config,k) for k in ('source','mood','seed')) or (config.mood=='radio' and config.radio!=self.config.radio)
            if config.radio!=self.config.radio:
                self.generator=Generator(self.generator.folder,config.radio.model_dump())
            self.config=config;self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_suffix('.tmp');tmp.write_text(config.model_dump_json(indent=2),encoding='utf-8');tmp.replace(self.path)
            if playout.ENABLED:
                with playout.LOCK:
                    playout.command(f'MIXER 1-5 VOLUME {self.effective_volume()} {playout.transition_frames(30)} LINEAR')
                    self.last_gain=self.effective_volume()
                    if shuffle_changed or source_changed:self.queued=None
                    if source_changed:self.pending=None;self.retry_at=0
                    if not config.enabled:playout.command('CLEAR 1-5');self.current=self.queued=None;self.pending=None
    def set_duck(self, enabled):
        with self.lock:
            if self.ducked==enabled:return
            self.ducked=enabled
            if playout.ENABLED:
                with playout.LOCK:
                    playout.command(f'MIXER 1-5 VOLUME {self.effective_volume()} {0 if enabled else playout.transition_frames(12)} LINEAR')
                    self.last_gain=self.effective_volume()

    def clip(self,name):
        if self.config.source=='playlist' and self.config.match_levels:
            prepared=self.levels.ready(name)
            if not prepared:raise ValueError('Track is not level-matched yet; existing audio retained')
            return json.dumps('/workspace/media/music/.skycam-levels/'+prepared)
        path='/workspace/runtime/music-generator/' if name.startswith(('skygen-v1-','skygen-v2-','skygen-v3-','skygen-v4-')) and (self.generator.folder/name).exists() else '/workspace/media/music/'
        return json.dumps(path+name,ensure_ascii=False)
    def transition(self):
        # Generated phrases share an absolute musical timeline. Overlapping them
        # shortens that timeline and creates double beats, so only disk tracks mix.
        if self.config.source!='playlist' or not self.config.crossfade_seconds:return ''
        return f' MIX {playout.transition_frames(self.config.crossfade_seconds*60)} LINEAR'

    def hold_phrase(self,current,root):
        if not current or not (self.generator.folder/current).is_file():return
        bg=root.find('.//layer_5/background/producer')
        if bg is None or bg.text=='empty':
            with playout.LOCK:
                playout.command(f'LOADBG 1-5 {self.clip(current)} LOOP AUTO')
            self.queued=current
            self.fallback_queued=True

    def queue_next(self,name):
        playout.command(f'LOADBG 1-5 {self.clip(name)}{self.transition()} AUTO')
        if self.config.source=='generated':
            # AUTO waits for foreground EOF. A fallback that already reached
            # program is looping; queue its successor BEFORE releasing that loop.
            # Also works after a controller restart, when Python forgot the flag.
            playout.command('CALL 1-5 LOOP 0')
        self.queued=name;self.fallback_queued=False

    def check(self):
        if not playout.ENABLED:return
        with self.lock:
            self.disk_files=sorted(p.name for p in self.folder.glob('*') if p.is_file() and not p.is_symlink() and p.suffix.lower() in {'.mp3','.wav','.flac','.ogg','.m4a','.aac'} and not any(c in p.name for c in '\r\n'))
            self.levels.folder=self.folder;self.levels.cache=self.folder/'.skycam-levels';self.levels.refresh()
            if self.config.source=='playlist':
                self.files=[name for name in self.disk_files if self.levels.ready(name)] if self.config.match_levels else self.disk_files
                if self.config.match_levels and not self.files:self.error='No prepared level-matched tracks; existing audio retained. Prepare the music library first.'
            if not self.config.enabled or (self.config.source=='playlist' and not self.files):return
            try:
                with playout.LOCK:
                    if not playout.STATUS['ready']:return
                    xml=playout.command('INFO 1',xml=True);root=ET.fromstring(xml[xml.index('<?xml'):])
                    node=root.find('.//layer_5/foreground/file/path')
                    current=Path(node.text).name if node is not None and node.text else None
                    if current:current=self.levels.original(current)
                    if self.pending:
                        name,started=self.pending
                        if current!=name and time.monotonic()-started<5:return
                        self.pending=None
                        if current!=name:
                            self.error='The selected track did not start; the current track is still playing'
                            return
                    # Quiet-hours gain must still update while synthesis is slow
                    # or backing off after failure. Rendering cannot defer it.
                    gain=self.effective_volume()
                    if gain!=self.last_gain:
                        playout.command(f'MIXER 1-5 VOLUME {gain} {playout.transition_frames(180)} LINEAR')
                        self.last_gain=gain
                # Synthesis never holds the shared playout lock.
                if self.config.source=='generated':
                    if time.monotonic()<self.retry_at:return
                    if self.render_job is not None and self.render_job.done():
                        job=self.render_job;self.render_job=None;job.result()
                    index=self.generator.index(current,self.config.seed,self.config.mood)
                    if index is None:index=0
                    names=[self.generator.name(self.config.seed,self.config.mood,i) for i in (index,index+1,index+2)]
                    missing=[i for i,name in enumerate(names) if not (self.generator.folder/name).exists()]
                    if missing and self.render_job is None:
                        self.render_job=self.render_pool.submit(render_phrase,self.generator,self.config.seed,self.config.mood,index+missing[0])
                    if any(i<2 for i in missing):
                        self.hold_phrase(current,root)
                        self.current=current
                        self.error='Preparing generated music; existing audio continues'
                        return
                    self.files=[name for name in names if (self.generator.folder/name).exists()]
                    self.generator.prune(set(names)|{current,self.queued})
                with playout.LOCK:
                    if self.config.source=='playlist' and current in self.disk_files and current not in self.files:
                        # A changed library/policy never cuts the active track.
                        self.queue_next(self.files[0]);self.current=current
                        self.error='Level-matched playlist will follow the current track'
                        return
                    if self.config.source=='generated' and current and current not in self.files:
                        # A mood/seed change prepares the next phrase, then lets the
                        # current file finish. Never restart the program music bus.
                        nxt=self.files[0]
                        bg=root.find('.//layer_5/background/producer')
                        if self.queued!=nxt or bg is None or bg.text=='empty':
                            self.queue_next(nxt)
                        self.current=current;self.error='New variation ready; changes at the next phrase boundary'
                        return
                    if current not in self.files:
                        current=self.pick_next(None);playout.command(f'PLAY 1-5 {self.clip(current)}')
                        playout.command(f'MIXER 1-5 VOLUME {self.effective_volume()}')
                        self.queued=None
                    bg=root.find('.//layer_5/background/producer')
                    if self.fallback_queued or current!=self.current or self.queued not in self.files or bg is None or bg.text=='empty':
                        nxt=self.pick_next(current)
                        self.queue_next(nxt)
                    if self.current and current!=self.current:self.history.append(self.current);self.history=self.history[-100:]
                    self.current=current;self.error=None
                    # Background music is the program audio bus while enabled.
                    for layer in [10]:playout.command(f'MIXER 1-{layer} VOLUME 0')
                    playout.CAMERA_AUDIO=False
            except Exception as exc:
                self.error=public_error(exc)[:200];self.retry_at=time.monotonic()+15
                # If generation fails, keep a valid phrase queued rather than
                # clearing the audio bus. Retry generation independently.
                if self.config.source=='generated' and self.current and (self.generator.folder/self.current).exists():
                    try:
                        with playout.LOCK:
                            playout.command(f'LOADBG 1-5 {self.clip(self.current)} LOOP AUTO')
                            self.fallback_queued=True
                    except Exception:pass
    def pick_next(self,current):
        if self.config.source=='generated':
            return self.files[(self.files.index(current)+1)%len(self.files)] if current in self.files else self.files[0]
        choices=[name for name in self.files if name!=current]
        if self.config.shuffle and choices:return random.choice(choices)
        return self.files[(self.files.index(current)+1)%len(self.files)] if current in self.files else self.files[0]
    def action(self,action,track=None):
        with self.lock:
            if self.config.source=='generated':raise ValueError('Track controls apply to the disk playlist. Generated music evolves automatically; change its mood or seed in music settings.')
            if not self.files:raise ValueError('The music folder is empty')
            if action=='play':
                if track not in self.files:raise ValueError('Choose a track from the music list')
                name=track
            elif action=='next':name=self.queued if self.queued in self.files else self.pick_next(self.current)
            elif action=='previous':
                name=next((x for x in reversed(self.history) if x in self.files),None)
                if name is None:name=self.files[(self.files.index(self.current)-1)%len(self.files)] if self.current in self.files else self.files[0]
                if self.history:self.history.pop()
            else:raise ValueError('Unknown music action')
            if not playout.ENABLED:raise ValueError('Music control is available on the broadcast host')
            with playout.LOCK:
                playout.command(f'PLAY 1-5 {self.clip(name)}{self.transition()}')
                playout.command(f'MIXER 1-5 VOLUME {self.effective_volume()}')
                if action!='previous' and self.current:self.history.append(self.current)
                self.current=name;self.queued=None;self.error=None
                self.pending=(name,time.monotonic())
                if not self.config.enabled:self.save(self.config.model_copy(update={'enabled':True}))
        self.check()
        return self.public()
    async def watch(self):
        while True:
            await asyncio.to_thread(self.check)
            await asyncio.sleep(2)
