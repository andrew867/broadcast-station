"""Bounded observations of existing counters, without another media decoder."""
import asyncio
from collections import deque
import copy
import math
from pathlib import Path
import threading
import time


def host_memory():
    try:
        fields={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
        return {'available_bytes':fields['MemAvailable'],'total_bytes':fields['MemTotal'],
                'swap_used_bytes':fields['SwapTotal']-fields['SwapFree']}
    except (OSError,ValueError,KeyError):return None


class Performance:
    def __init__(self,capacity=720,history=None):
        self.rows=deque(maxlen=capacity);self.lock=threading.Lock()
        self.history=history

    def sample(self,status,now=None,memory=None):
        now=time.time() if now is None else now
        # Status writers replace each nested observation atomically. Copy only
        # the small fields used here, without taking the native command lock.
        age=max(0,now-status.get('checked_at',0));fresh=bool(status.get('checked_at') and age<5)
        out=dict(status.get('output') or {});fps=out.get('measured_fps')
        if not fresh or not isinstance(fps,(int,float)) or not math.isfinite(fps):fps=None
        cameras={k:copy.deepcopy({field:v.get(field) for field in ('frame_age_s','native_frame_age_s','display','video_frame','native_ready','playout_active','generation','state','native_metrics','transport','recovery_note')})
                 for k,v in list(status.get('cameras',{}).items())}
        row={'at':now,'status_age_s':round(age,2) if status.get('checked_at') else None,
             'fps':fps,'moving':bool(fresh and out.get('moving')),'frames':out.get('frames') if fresh else None,
             'scene':(status.get('program') or {}).get('camera'),'sources':cameras,
             'transition':copy.deepcopy(status.get('transition')),'memory':memory,'network':copy.deepcopy(status.get('network')),
             'graphics':dict(status.get('graphics_memory') or {})}
        with self.lock:self.rows.append(row)
        return row

    def public(self):
        with self.lock:rows=copy.deepcopy(list(self.rows))
        rates=[r['fps'] for r in rows if r['fps'] is not None]
        transitions={r['transition']['at']:r['transition'] for r in rows if r.get('transition') and 'at' in r['transition']}
        return {'samples':rows,'capacity':self.rows.maxlen,'interval_s':5,
                'summary':{'samples':len(rows),'valid_samples':len(rates),'stale_samples':len(rows)-len(rates),
                  'minimum_fps':min(rates) if rates else None,'maximum_fps':max(rates) if rates else None,
                  'average_fps':round(sum(rates)/len(rates),2) if rates else None,
                  'transitions':len(transitions),'fallback_cuts':sum(bool(t.get('fallback_cut')) for t in transitions.values())},
                'limits':'Rolling samples of the encoded-output counter, not distinct-picture FPS or downstream playback. Source age is independent health-reader delivery age, not camera capture age. Native queue age measures only the decoded output queue; it excludes network and upstream delay. Decoded drops are safe complete-picture skips. Transport counters count only RTP loss reported by the local hub and reset with that service; absence of a report is not proof of undamaged video. History is in memory and resets when the controller restarts.'}

    async def watch(self,get_status):
        while True:
            row=self.sample(get_status(),memory=host_memory())
            if self.history:
                try:await asyncio.to_thread(self.history.add,row)
                except Exception:self.history.error='Performance history unavailable; program is unaffected'
            await asyncio.sleep(5)
