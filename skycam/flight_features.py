"""Received-aircraft selection, bounded trails and a shared altitude palette."""
import math
import time

BANDS=((10000,'#55d8c4','BELOW 10,000'),(25000,'#ffce70','10,000 TO 24,999'),(float('inf'),'#cfabff','25,000+'))

def altitude_color(plane):
    if plane.get('stale'):return '#8f999f'
    value=plane.get('altitude_ft')
    if not isinstance(value,(int,float)) or not math.isfinite(value):return '#ffffff'
    return next(color for ceiling,color,_ in BANDS if value<ceiling)

def trail_segments(points, now, age=120, gap=10):
    result=[];segment=[];last=None
    for p in points:
        if not 0<=now-p['time']<=age:continue
        if last is not None and (p['time']-last['time']>gap or p['time']<=last['time']):
            if len(segment)>1:result.append(segment)
            segment=[]
        segment.append([p['lat'],p['lon']]);last=p
    if len(segment)>1:result.append(segment)
    return result

class Spotlight:
    def __init__(self):self.selected=None;self.since=0;self.manual=None
    def select(self, aircraft, healthy, now=None):
        now=time.monotonic() if now is None else now
        eligible=[p for p in aircraft if healthy and not p.get('stale')]
        if self.manual:return next((p for p in eligible if p['hex']==self.manual),None)
        old=next((p for p in eligible if p['hex']==self.selected),None)
        if old is not None and now-self.since<45:return old
        # Cycle predictable received identities, without guessing flight routes or aircraft types.
        choices=sorted(eligible,key=lambda p:p['hex'])
        candidate=next((p for p in choices if self.selected is None or p['hex']>self.selected),choices[0] if choices else None)
        self.selected=candidate['hex'] if candidate else None;self.since=now
        return candidate

def audio_levels(root, now=None):
    values=root.findall('./mixer/audio/volume')[:2]
    try:levels=[round(max(-90,min(0,20*math.log10(max(abs(int(v.text)),1)/2147483647))),1) for v in values]
    except (ValueError,TypeError):levels=[]
    return {'at':time.time() if now is None else now,'dbfs':levels,'available':len(levels)==2,
            'basis':'Sampled native program mix peaks; not a loudness or downstream audio test'}
