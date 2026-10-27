"""Automatic cue eligibility, independent of acquisition and manual takes."""
import asyncio
import json
import math
import threading
import time
from pathlib import Path
from typing import Literal
from pydantic import Field
from .models import StrictModel
from .storage import save_json


class RotationConfig(StrictModel):
    version: Literal[1] = 1
    skip_unavailable: bool = True
    unavailable_after_s: int = Field(default=180, ge=15, le=3600)
    recovery_after_s: int = Field(default=10, ge=3, le=120)


class CameraRotation:
    def __init__(self, data, cameras, monotonic=time.monotonic, wall=time.time):
        self.path=Path(data)/'broadcast/camera-rotation.json'
        self.health_path=Path(data)/'source-health.json'
        self.cameras=cameras;self.monotonic=monotonic;self.wall=wall
        self.lock=threading.RLock();self.states={};self.last_sample=None;self.error=None
        self.config=RotationConfig()
        if self.path.exists():
            try:self.config=RotationConfig.model_validate_json(self.path.read_text())
            except (ValueError,OSError):self.error='Camera rotation settings could not be read; defaults are active.'

    def save(self, config):
        with self.lock:
            save_json(self.path,config.model_dump());self.config=config;self.error=None

    def sample(self, payload=None):
        now=self.monotonic();wall=self.wall()
        if payload is None:
            try:
                if self.health_path.stat().st_size>1_000_000:raise ValueError('Oversized health file')
                payload=json.loads(self.health_path.read_text())
            except (OSError,ValueError):payload={}
        if not isinstance(payload,dict):payload={}
        checked=payload.get('checked_at');rows=payload.get('cameras',{})
        valid=isinstance(checked,(float,int)) and math.isfinite(checked) and 0<=wall-checked<=3
        if not isinstance(rows,dict):rows={}
        with self.lock:
            gap=self.last_sample is not None and now-self.last_sample>3
            self.last_sample=now
            for camera,source in list(self.cameras.items()):
                state=self.states.setdefault(camera,{'down_since':None,'healthy_since':None,'skipped':False})
                row=rows.get(camera,{});row=row if isinstance(row,dict) else {}
                frame=row.get('last_frame_at')
                fresh=(valid and row.get('ready') is True and isinstance(frame,(float,int))
                       and math.isfinite(frame) and 0<=wall-frame<2.5)
                if not source.get('enabled',True):
                    state.update(down_since=None,healthy_since=None,skipped=True,reason='disabled')
                    continue
                if fresh:
                    if state['healthy_since'] is None or gap:state['healthy_since']=now
                    if not state['skipped'] or now-state['healthy_since']>=self.config.recovery_after_s:
                        state.update(down_since=None,skipped=False,reason='ready')
                    else:state['reason']='recovering'
                else:
                    state['healthy_since']=None
                    if state['down_since'] is None:state['down_since']=now
                    if now-state['down_since']>=self.config.unavailable_after_s:state['skipped']=True
                    state['reason']='unavailable' if state['skipped'] else 'grace'
            for camera in set(self.states)-set(self.cameras):self.states.pop(camera)

    def eligible(self, scene):
        # Maps, quads and manual scene availability are unaffected.
        with self.lock:
            source=self.cameras.get(scene)
            if source is None:return True
            if not source.get('enabled',True):return False
            return not self.config.skip_unavailable or not self.states.get(scene,{}).get('skipped',False)

    def public(self):
        with self.lock:
            now=self.monotonic()
            return {'config':self.config.model_dump(),'error':self.error,'cameras':{
                key:{'eligible':self.eligible(key),'reason':row.get('reason'),
                     'unavailable_s':round(now-row['down_since'],1) if row['down_since'] is not None else 0}
                for key,row in self.states.items()}}

    async def watch(self):
        while True:
            self.sample()
            await asyncio.sleep(1)
