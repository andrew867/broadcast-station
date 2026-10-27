"""Original 80 BPM study radio, rendered ahead with bounded voices and tails."""
from bisect import bisect_left
from functools import lru_cache
from pathlib import Path
import json
import math
import os
import subprocess
import numpy as np
from scipy.signal import butter, sosfilt
from . import study_songs as songs
from .strudel_music import recorded_piano
from .lofi_music import kit
from .study_radio_config import StudyRadioConfig

RATE=24000
TAIL=9
KINDS={'piano','rhodes','flute','guitar','bass','bed','drum'}

def canonical(options=None):
    return StudyRadioConfig.model_validate(options or {}).model_dump_json()

@lru_cache(maxsize=6)
def compose(seed,number,config):
    options=json.loads(config)
    result=subprocess.run(['node','--max-old-space-size=96',
        str(Path(__file__).parent/'assets/study-radio-arrange.mjs'),str(seed),str(number),config],
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12,
        check=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if len(result.stdout)>2_000_000:raise ValueError('Oversized radio arrangement')
    rows=json.loads(result.stdout)['events']
    if not 100<=len(rows)<=4000:raise ValueError('Invalid radio arrangement')
    phrase_frames=round(64*60/options['bpm']*48000)
    beat=phrase_frames/(64*48000)
    events=[]
    for row in rows:
        b,n,g,p,d=(float(row[k]) for k in ('beat','note','gain','pan','duration'))
        valid_pitch=n in range(6) if row['kind']=='drum' else 24<=n<=90
        if not (all(math.isfinite(v) for v in (b,n,g,p,d)) and 0<=b<256 and valid_pitch):
            raise ValueError('Invalid radio note')
        if row['kind'] not in KINDS or not 0<=g<=.3 or not -1<=p<=1 or not 0<d<=8:
            raise ValueError('Invalid radio voice')
        events.append(songs.Note(round(b*beat*RATE),row['kind'],int(n),g,p,d))
    events.sort(key=lambda e:e.start)
    return tuple(events),tuple(e.start for e in events)

@lru_cache(maxsize=96)
def instrument(kind,note,duration):
    if kind=='piano':return recorded_piano('hifipiano',note,duration)
    duration=min(TAIL,float(duration)+.7)
    t=np.arange(round(duration*RATE),dtype=np.float64)/RATE
    f=440*2**((note-69)/12);phase=2*np.pi*f*t
    if kind=='rhodes':
        # Harmonic reed colour, no high inharmonic bell transient.
        body=np.sin(phase)+.28*np.sin(2*phase)*np.exp(-t*2)+.07*np.sin(3*phase)*np.exp(-t*4)
        body+=.10*np.sin(phase*.999+.3)
        env=(1-np.exp(-t*40))*np.exp(-t*.85)
    elif kind=='flute':
        body=np.sin(phase+.008*np.sin(t*29))+.13*np.sin(2*phase)+.035*np.sin(3*phase)
        env=(1-np.exp(-t*11))*np.exp(-t*1.7)
    elif kind=='guitar':
        body=np.sin(phase)+.3*np.sin(2*phase)*np.exp(-t*3)+.13*np.sin(3*phase)*np.exp(-t*6)
        env=(1-np.exp(-t*75))*np.exp(-t*2.1)
    elif kind=='bass':
        body=np.sin(phase)+.24*np.sin(2*phase)*np.exp(-t*2)
        env=(1-np.exp(-t*48))*np.exp(-t*1.15)
    elif kind=='bed':
        body=np.sin(phase)+.08*np.sin(phase*.999)
        env=(1-np.exp(-t*2))*np.exp(-t*.25)
    else:raise ValueError('Unknown radio voice')
    dry=np.tanh(body*.85)*env*np.clip((duration-t)/.5,0,1)
    if kind not in ('bass','bed'):
        wet=dry.copy()
        for seconds,gain in ((.083,.10),(.157,.065),(.305,.035)):
            off=round(seconds*RATE)
            if off<len(dry):wet[off:]+=dry[:-off]*gain
        dry=wet
    return dry.astype(np.float32)

@lru_cache(maxsize=4)
def filtered_kit(seed):
    return tuple(sosfilt(butter(2,4200 if i in (0,1,2) else 7000,fs=RATE,output='sos'),x).astype(np.float32)
                 for i,x in enumerate(kit(seed%64,RATE)))

@lru_cache(maxsize=3)
def atmosphere(seed):
    # Circular filtered noise has exact wrap continuity. These are original
    # synthetic rain/vinyl textures, not third-party ambience recordings.
    count=RATE*23;rng=np.random.default_rng(seed^0x517A)
    freq=np.fft.rfftfreq(count,1/RATE)
    rain=[];vinyl=[]
    for _ in range(2):
        noise=np.fft.rfft(rng.normal(size=count))
        shape=(freq/np.maximum(freq,160))/(1+(freq/2400)**2)
        audio=np.fft.irfft(noise*shape,n=count);audio/=max(float(np.std(audio)),1e-6)
        rain.append(audio*.006)
        hiss=np.fft.irfft(np.fft.rfft(rng.normal(size=count))/(1+(freq/1500)**2),n=count)
        hiss/=max(float(np.std(hiss)),1e-6)
        pops=np.zeros(count)
        for onset in rng.integers(0,count-300,size=13):
            x=np.arange(240)/RATE
            pops[onset:onset+240]+=.024*np.sin(2*np.pi*900*x)*np.exp(-x*600)
        vinyl.append(hiss*.0025+pops)
    return np.column_stack(rain).astype(np.float32),np.column_stack(vinyl).astype(np.float32)

def render_low(start,count,seed,config):
    options=json.loads(config);phrase=round(64*60/options['bpm']*48000)
    song_samples=phrase*2
    audio=np.zeros((count,2),dtype=np.float32)
    for number in range(max(0,(start-TAIL*RATE)//song_samples),(start+count-1)//song_samples+1):
        events,starts=compose(seed,number,config);origin=number*song_samples
        for e in events[bisect_left(starts,start-origin-TAIL*RATE):bisect_left(starts,start+count-origin)]:
            voice=filtered_kit((seed+number)%64)[e.pitch] if e.kind=='drum' else instrument(e.kind,e.pitch,e.duration)
            a=max(start,origin+e.start);b=min(start+count,origin+e.start+len(voice))
            if a>=b:continue
            sound=voice[a-origin-e.start:b-origin-e.start]*e.gain
            audio[a-start:b-start,0]+=sound*(1-e.pan)
            audio[a-start:b-start,1]+=sound*(1+e.pan)
    if options['rain'] or options['vinyl']:
        rain,vinyl=atmosphere(seed)
        indices=np.arange(start,start+count)%len(rain)
        audio+=rain[indices]*options['rain']+vinyl[indices]*options['vinyl']
    return (np.tanh(audio*1.2)*.68).astype(np.float32)

def samples(start,count,seed,options=None):
    if count<=0:return np.empty((0,2),dtype=np.float32)
    config=canonical(options)
    base=start//2;last=(start+count-1)//2+1
    low=render_low(base,last-base+1,seed,config)
    position=np.arange(count)+start%2;index=position//2
    blend=(position%2).astype(np.float32)*.5
    return low[index]*(1-blend[:,None])+low[index+1]*blend[:,None]

def song_info(seed,phrase,options=None):
    opts=json.loads(canonical(options));number=phrase//4
    def title(n):
        i=(seed+n*37)%(len(songs.PLACES)*len(songs.TIMES))
        return f'{songs.PLACES[i%len(songs.PLACES)]} {songs.TIMES[i//len(songs.PLACES)]}'
    return {'number':number+1,'title':title(number),'next_title':title(number+1),
        'key':('C','C#','D','Eb','E','F','F#','G','G#','A','Bb','B')[(seed%12+number*5+opts['transpose'])%12]+' minor',
        'duration_seconds':round(64*60/opts['bpm']*48000)*4/48000,
        'section':' / '.join(songs.SECTIONS[phrase%4*2:phrase%4*2+2]),'phrase_in_song':phrase%4+1,
        'palette':('Upright and flute','Soft Rhodes and guitar','Upright and Rhodes')[number%3],
        'engine':'Strudel 1.2.6 / original Study Radio arrangement'}
