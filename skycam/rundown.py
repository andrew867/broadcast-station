"""Persistent timed rundown with explicit manual hold and monotonic timing."""
import asyncio
import copy
from contextlib import contextmanager
import json
import threading
import time
from pathlib import Path
from typing import Literal
from pydantic import Field
from .models import StrictModel

class Cue(StrictModel):
    camera: str = Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,47}$')
    seconds: int = Field(default=30,ge=5,le=3600)
    scene: Literal['standard','clean','breaking'] = 'standard'
    condition: Literal['auto','always','when-current','when-exception'] = 'auto'

class RundownConfig(StrictModel):
    cues: list[Cue] = Field(default_factory=lambda:[Cue(camera=c,seconds=d) for c,d in [('cam1',30),('cam2',30),('cam3',45),('cam4',45),('quad',30)]],min_length=1,max_length=30)
    transition: Literal['dissolve','cut'] = 'dissolve'
    resume_after_restart: bool = False

class Rundown:
    def __init__(self,data:Path,apply,ready=None,prepare=None,recovery_ready=None):
        self.path=data/'broadcast'/'rundown.json';self.apply=apply;self.lock=threading.RLock()
        self.config=RundownConfig.model_validate_json(self.path.read_text(encoding='utf-8')) if self.path.exists() else RundownConfig()
        self.dayparts=None;self.daypart=None
        self.enabled=False;self.index=0;self.deadline=0.;self.error=None;self.note='Manual hold'
        self.clock=None;self.block=None;self.block_index=0;self.clock_preview=None;self.clock_error=None
        self.followups=None;self.followup_take=None;self.followup_valid=None;self.interlude=None;self.followup_queue=[]
        self.ready=ready or (lambda _:True);self.prepare=prepare;self.prepared_index=None
        self.eligible=lambda _:True
        self.condition_eligible=lambda _scene,_condition:True
        self.recovery_ready=recovery_ready or (lambda:True)
        self.intent_path=self.path.with_name('rundown-intent.json');self.resume_pending=False
        try:
            intent=json.loads(self.intent_path.read_text(encoding='utf-8'))
            if not isinstance(intent,dict):raise ValueError('Invalid saved rundown intent')
            self.resume_pending=self.config.resume_after_restart and intent.get('running') is True
            self.index=max(0,min(int(intent.get('index',0)),len(self.config.cues)-1))
        except (OSError,ValueError,TypeError):pass
        if self.resume_pending:self.note='Waiting for program output before resuming rotation'
        self._status={};self._publish_status()

    def _publish_status(self):
        block={k:self.block[k] for k in ('name','include_alerts','rule_id','scheduled_at')} if self.block else None
        if block:block.update(index=self.block_index,total=len(self.block['config'].cues),camera=self._current_cue().camera)
        self._status={**self.config.model_dump(),'enabled':self.enabled,'resume_pending':self.resume_pending,
            'daypart':{'name':self.daypart['name'],'config':self.daypart['config'].model_dump()} if self.daypart else None,
            'index':self.index,'note':self.note,'error':self.error,'interlude':copy.deepcopy(self.interlude),
            'block':block,'active_cue':self._current_cue().model_dump(),'clock_error':self.clock_error,'observed_at':time.time(),
            '_monotonic':time.monotonic(),'_deadline':self.deadline}

    @contextmanager
    def _editing(self):
        # Mutations remain serialized. Readers use the last complete snapshot
        # while source warmup or a native take is waiting on hardware.
        with self.lock:
            try:yield
            finally:self._publish_status()
    def _persist_intent(self):
        self.intent_path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.intent_path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'running':self.enabled,'index':self.index}),encoding='utf-8')
        tmp.replace(self.intent_path)
    def public(self):
        acquired=self.lock.acquire(blocking=False)
        try:
            if acquired:self._publish_status()
            result=copy.deepcopy(self._status)
        finally:
            if acquired:self.lock.release()
        now=time.monotonic();deadline=result.pop('_deadline')
        result['snapshot_age_s']=max(0,now-result.pop('_monotonic'))
        result['busy']=not acquired
        result['remaining_s']=max(0,deadline-now) if result['enabled'] else None
        return result
    def scene_timing(self,camera):
        state=self.public();cue=state['active_cue']
        if not state['enabled'] or state['interlude'] or cue['camera']!=camera:return None
        return {'seconds':cue['seconds'],'elapsed':max(0,cue['seconds']-(state['remaining_s'] or 0))}

    def save(self,config):
        with self._editing():
            self.pause('Playlist saved, press Start to run it');self.config=config;self.index=0
            self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_suffix('.tmp');tmp.write_text(config.model_dump_json(indent=2),encoding='utf-8');tmp.replace(self.path)
    def pause(self,note='Manual hold'):
        with self._editing():
            self.daypart=None;self.index=min(self.index,len(self.config.cues)-1)
            self.block=None;self.clock_preview=None
            self.enabled=False;self.resume_pending=False;self.interlude=None;self.followup_queue=[];self.note=note;self._persist_intent()
    def _background_config(self):return self.daypart['config'] if self.daypart else self.config
    def _current_cue(self):return self._active_config().cues[self.block_index if self.block else self.index]
    def _active_config(self):return self.block['config'] if self.block else self._background_config()
    def _sync_daypart(self):
        selected=self.dayparts.selection() if self.dayparts else None
        if (selected or {}).get('key')==(self.daypart or {}).get('key'):return False
        self.daypart={**selected,'config':RundownConfig.model_validate(selected['config'])} if selected else None
        self.index=0;self.prepared_index=None
        return True
    def _end_block(self):
        self.block=None;self.block_index=0;self.clock_preview=None;self.interlude=None;self.followup_queue=[]
        self._sync_daypart()
        self._advance(self.index)
    def _start_block(self,block):
        config=RundownConfig.model_validate(block['config'])
        self.index=(self.index+1)%len(self._background_config().cues)
        self.block={**block,'config':config};self.block_index=0;self.prepared_index=None;self.clock_preview=None
        self._advance(0)
    def _follow_next(self):
        while self.followup_queue:
            cue=self.followup_queue.pop(0)
            try:
                if not self.followup_take or not self.followup_take(cue):continue
                self.interlude=cue;self.deadline=time.monotonic()+cue['seconds'];self.prepared_index=None;self.error=None
                self.note='Weather alert pages following the forecast';return True
            except (ValueError,RuntimeError,OSError) as exc:self.error=str(exc)
        self.interlude=None;return False
    def _finish_cue(self):
        if not self.interlude and self.followups and (not self.block or self.block['include_alerts']):
            self.followup_queue=self.followups(self._current_cue().camera)
        if not self._follow_next():self._after_cue()
    def _after_cue(self):
        if self.block:
            if self.block_index+1>=len(self.block['config'].cues):self._end_block()
            else:self._advance(self.block_index+1)
        else:
            changed=self._sync_daypart()
            self._advance(0 if changed else (self.index+1)%len(self._background_config().cues))
    def _take(self,index):
        config=self._active_config();cue=config.cues[index]
        self.apply(cue.camera,cue.scene,0 if config.transition=='cut' else 30)
        if self.block:self.block_index=index
        else:self.index=index
        self.deadline=time.monotonic()+cue.seconds;self.error=None;self.prepared_index=None
        self._persist_intent()
    def _advance(self,index):
        skipped=[];config=self._active_config()
        # A block plays through once; failures never wrap back to its first cue.
        indices=range(index,len(config.cues)) if self.block else [(index+i)%len(config.cues) for i in range(len(config.cues))]
        for candidate in indices:
            cue=config.cues[candidate]
            if not self.eligible(cue.camera) or not self.condition_eligible(cue.camera,cue.condition) or not self.ready(cue.camera):skipped.append(cue.camera);continue
            try:
                self._take(candidate)
                self.note=(self.block['name'] if self.block else 'Automatic rotation')+('; skipped '+', '.join(skipped) if skipped else '')
                return
            except (ValueError,RuntimeError,OSError) as exc:
                skipped.append(cue.camera);self.error=str(exc)
        if self.block:self._end_block();return
        # A failed source never disables the clock or tears down the current PGM.
        try:
            self.apply('map','standard',0)
            self.note='No ready scheduled camera; holding the airspace map'
        except (ValueError,RuntimeError,OSError) as exc:
            self.error=str(exc);self.note='Holding current program; retrying ready sources'
        self.deadline=time.monotonic()+5;self.prepared_index=None
    def action(self,action):
        with self._editing():
            if action=='pause':self.pause();return
            if action not in ('start','next'):raise ValueError('Unknown rundown action')
            if action=='start':
                self.enabled=True;self.interlude=None;self.followup_queue=[];self.block=None;self.clock_preview=None
                if self.clock:self.clock.armed_at=time.time()
                self._sync_daypart()
            self.resume_pending=False;self._persist_intent()
            if action=='start':self._advance(0)
            else:self._finish_cue()
    def advance_due(self):
        with self._editing():
            if self.resume_pending:
                if not self.recovery_ready():return
                self.resume_pending=False;self.enabled=True
                self._sync_daypart()
                self._advance(self.index)
                return
            if not self.enabled:return
            if self.clock:
                try:
                    block=self.clock.claim_due(busy=bool(self.block or self.interlude))
                    if block:self._start_block(block);return
                    self.clock_error=None
                except (ValueError,RuntimeError,OSError) as exc:self.clock_error=str(exc)[:160]
            if self.interlude and self.followup_valid and not self.followup_valid(self.interlude['token']):
                if not self._follow_next():self._after_cue()
                return
            if time.monotonic()>=self.deadline:
                self._finish_cue();return
            if not self.block and not self.interlude and self.clock and self.prepare:
                next_block=self.clock.upcoming()
                if next_block and 0<next_block['at']-time.time()<=10:
                    if self.clock_preview!=next_block['slot']:
                        try:
                            row=self.clock.resolve(next_block['rule']['playlist_id'])
                            cue=next((c for c in RundownConfig.model_validate(row['config']).cues if self.eligible(c.camera) and self.condition_eligible(c.camera,c.condition) and self.ready(c.camera)),None)
                            if cue:self.prepare(cue.camera,cue.scene)
                            self.clock_preview=next_block['slot']
                        except (ValueError,RuntimeError,OSError,KeyError) as exc:self.clock_error=str(exc)[:160]
                    return
            if self.interlude or (self.followups and self._current_cue().camera=='weather' and (not self.block or self.block['include_alerts'])):return
            if self.prepare and self.deadline-time.monotonic()<10:
                config=self._active_config();current=self.block_index if self.block else self.index
                indices=range(current+1,len(config.cues)) if self.block else [(current+i)%len(config.cues) for i in range(1,len(config.cues)+1)]
                for index in indices:
                    cue=config.cues[index]
                    if self.eligible(cue.camera) and self.condition_eligible(cue.camera,cue.condition) and self.ready(cue.camera):
                        if self.prepared_index!=index:
                            try:self.prepare(cue.camera,cue.scene);self.prepared_index=index
                            except (ValueError,RuntimeError,OSError) as exc:self.error=str(exc)
                        break
    async def watch(self):
        while True:
            try:await asyncio.to_thread(self.advance_due)
            except Exception as exc:
                self.error=str(exc)[:200]
                self.note='Rotation will retry; current program remains on air'
                await asyncio.sleep(2)
            await asyncio.sleep(.1)
