"""Optional local-time background loops, applied only at cue boundaries."""
from datetime import datetime
import hashlib
import json
import threading
import time
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from .map_theme import TIMEZONE
from .models import StrictModel
from .rundown_library import LibraryConflict
from .storage import save_json


def minute(value):
    hour, part = map(int, value.split(':'))
    return hour * 60 + part


def contains(start, end, current):
    return start <= current < end if start < end else current >= start or current < end


class Daypart(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    playlist_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    start: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    end: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')


class DaypartConfig(StrictModel):
    enabled: bool = False
    periods: list[Daypart] = Field(default_factory=list, max_length=8)

    @model_validator(mode='after')
    def no_overlap(self):
        used = set()
        for period in self.periods:
            start, end = minute(period.start), minute(period.end)
            if start == end:
                raise ValueError('Start and end must differ; use two periods for a full day')
            span = {m for m in range(1440) if contains(start, end, m)}
            if span & used:
                raise ValueError('Daypart times must not overlap')
            used |= span
        return self


class DaypartWrite(StrictModel):
    expected_revision: int = Field(ge=0)
    config: DaypartConfig


class Dayparts:
    def __init__(self, data, resolve):
        self.path=data/'broadcast'/'dayparts.json';self.resolve=resolve
        self.lock=threading.RLock();self.revision=0;self.config=DaypartConfig();self.error=None
        try:
            if self.path.exists():
                saved=json.loads(self.path.read_text(encoding='utf-8'))
                self.config=DaypartConfig.model_validate(saved['config']);self.revision=saved['revision']
        except (OSError,ValueError,KeyError,TypeError):
            self.error='Daypart settings could not be read. The regular background loop remains available.'

    def save(self, body):
        with self.lock:
            if body.expected_revision != self.revision:
                raise LibraryConflict('Dayparts changed in another window. Reload before saving.')
            for period in body.config.periods:self.resolve(period.playlist_id)
            save_json(self.path,{'revision':self.revision+1,'config':body.config.model_dump()})
            self.config=body.config;self.revision+=1;self.error=None

    def selection(self, now=None):
        with self.lock:
            if not self.config.enabled:return None
            local=datetime.fromtimestamp(time.time() if now is None else now,ZoneInfo(TIMEZONE))
            current=local.hour*60+local.minute
            for period in self.config.periods:
                if not contains(minute(period.start),minute(period.end),current):continue
                try:
                    row=self.resolve(period.playlist_id)
                    key=hashlib.sha256(json.dumps([period.model_dump(),row['config']],sort_keys=True).encode()).hexdigest()
                    self.error=None
                    return {'key':key,'name':period.name,'playlist_id':period.playlist_id,'config':row['config']}
                except (ValueError,KeyError,RuntimeError) as exc:
                    self.error='Daypart unavailable: '+str(exc)[:160]
                    return None
            self.error=None
            return None

    def public(self, now=None):
        with self.lock:
            selected=self.selection(now)
            return {'revision':self.revision,'config':self.config.model_dump(),'timezone':TIMEZONE,
                    'selected':selected['name'] if selected else None,'error':self.error}
