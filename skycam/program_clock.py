"""Wall-clock block eligibility. Playback durations remain monotonic in Rundown."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import json,threading,time
from typing import Literal
from pydantic import Field,model_validator
from .models import StrictModel
from .map_theme import TIMEZONE
from .storage import save_json
from .rundown_library import LibraryConflict

class ClockRule(StrictModel):
    id:str=Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,47}$')
    playlist_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    every_minutes:Literal[5,10,15,20,30,60]=10
    offset_minutes:int=Field(default=0,ge=0,le=59)
    priority:int=Field(default=0,ge=0,le=99)
    condition:Literal['always','power-outages']='always'
    include_alerts:bool=False
    enabled:bool=True
    @model_validator(mode='after')
    def offset_in_period(self):
        if self.offset_minutes>=self.every_minutes:raise ValueError('Offset must be smaller than the interval')
        return self

class ClockConfig(StrictModel):
    enabled:bool=False
    rules:list[ClockRule]=Field(default_factory=list,max_length=12)
    @model_validator(mode='after')
    def unique_ids(self):
        if len({r.id for r in self.rules})!=len(self.rules):raise ValueError('Each clock rule needs a unique ID')
        return self

class ClockWrite(StrictModel):
    expected_revision:int=Field(ge=0)
    config:ClockConfig

class ProgramClock:
    def __init__(self,data,resolve,now=None):
        self.path=data/'broadcast'/'program-clock.json';self.history_path=self.path.with_name('program-clock-history.json')
        self.eligible=lambda condition:condition=='always';self.resolve=resolve;self.lock=threading.RLock();self.config=ClockConfig();self.revision=0;self.error=None
        self.armed_at=time.time() if now is None else now;self.history=[]
        try:
            if self.path.exists():
                raw=json.loads(self.path.read_text(encoding='utf-8'));self.config=ClockConfig.model_validate(raw['config']);self.revision=raw['revision']
            if self.history_path.exists():
                history=json.loads(self.history_path.read_text(encoding='utf-8'))
                if not isinstance(history,list) or any(not isinstance(r,dict) or 'slot' not in r for r in history):raise ValueError('Invalid clock history')
                self.history=history[-256:]
        except (ValueError,KeyError,TypeError,OSError):self.error='Saved program clock could not be read; scheduling is disabled.';self.config.enabled=False
    def save(self,body,now=None):
        with self.lock:
            if self.error:raise RuntimeError(self.error)
            if body.expected_revision!=self.revision:raise LibraryConflict('Program clock changed in another window. Reload before saving.')
            for rule in body.config.rules:self.resolve(rule.playlist_id)
            save_json(self.path,{'revision':self.revision+1,'config':body.config.model_dump()})
            self.config=body.config;self.revision+=1;self.armed_at=time.time() if now is None else now
    def _candidate(self,stamp):
        local=datetime.fromtimestamp(stamp,ZoneInfo(TIMEZONE))
        rules=[r for r in self.config.rules if r.enabled and local.minute%r.every_minutes==r.offset_minutes]
        # Once per local clock minute, including the repeated autumn hour.
        slot=local.strftime('%Y-%m-%dT%H:%M')
        if not rules or any(h['slot']==slot for h in self.history):return None
        return slot,sorted(rules,key=lambda r:(-r.priority,-r.every_minutes,r.id))
    def upcoming(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            if not self.config.enabled or self.error:return None
            start=int(now//60)*60+60
            for stamp in range(start,start+7201,60):
                candidate=self._candidate(stamp)
                if candidate:
                    slot,rules=candidate
                    rules=[r for r in rules if self.eligible(r.condition)]
                    if not rules:continue
                    rule=rules[0]
                    try:name=self.resolve(rule.playlist_id)['name']
                    except (KeyError,ValueError,RuntimeError):name='Unavailable playlist'
                    return {'slot':slot,'at':stamp,'local_time':datetime.fromtimestamp(stamp,ZoneInfo(TIMEZONE)).isoformat(),'rule':rule.model_dump(),'name':name}
        return None
    def _record(self,slot,rule,outcome,now,detail=''):
        history=[*self.history,{'slot':slot,'rule_id':rule.id,'outcome':outcome,'at':now,'detail':detail}][-256:]
        save_json(self.history_path,history);self.history=history
    def claim_due(self,busy=False,now=None):
        now=time.time() if now is None else now
        with self.lock:
            if not self.config.enabled or self.error:return None
            stamp=int(now//60)*60
            # Never replay missed breaks after startup/hold or a forward clock jump.
            if stamp<=self.armed_at or now-stamp>5:return None
            candidate=self._candidate(stamp)
            if not candidate:return None
            slot,rules=candidate
            eligible=[r for r in rules if self.eligible(r.condition)]
            if not eligible:self._record(slot,rules[0],'skipped_condition',now);return None
            rules=eligible;rule=rules[0]
            if busy:self._record(slot,rule,'skipped_busy',now);return None
            try:block=self.resolve(rule.playlist_id)
            except (KeyError,ValueError,RuntimeError) as exc:self._record(slot,rule,'unavailable',now,str(exc));return None
            self._record(slot,rule,'claimed',now,'Supersedes '+', '.join(r.id for r in rules[1:]) if len(rules)>1 else '')
            return {'name':block['name'],'config':block['config'],'include_alerts':rule.include_alerts,'rule_id':rule.id,'scheduled_at':stamp}
    def public(self,now=None):
        with self.lock:return {'revision':self.revision,'config':self.config.model_dump(),'error':self.error,'next':self.upcoming(now),'history':self.history[-12:],'timezone':TIMEZONE}
