"""Strudel arrangements rendered ahead with original, cached PCM instruments.

The bundled pinned Strudel program schedules notes in a bounded child process.
No browser, network samples, live synth or GPU is used by production music.
"""
from functools import lru_cache
from pathlib import Path
import json
import math
import subprocess
import os
import numpy as np
from . import study_songs as songs

PALETTES = ('Dusty upright', 'Tape piano', 'Felt keys')
KINDS = {'dustkeys','tapepiano','softorgan','roundbass','warmbed','drum'}

@lru_cache(maxsize=4)
def compose(seed, number, warm=False):
    result = subprocess.run(['node', '--max-old-space-size=96',
        str(Path(__file__).parent/'assets/strudel-arrange.mjs'), str(seed), str(number)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=12, check=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if len(result.stdout)>2_000_000: raise ValueError('Oversized music arrangement')
    data=json.loads(result.stdout)
    rows=data['events']
    if not 100<=len(rows)<=6000: raise ValueError('Invalid music arrangement length')
    events=[]
    for row in rows:
        beat, pitch, gain, pan, duration = (float(row[k]) for k in ('beat','note','gain','pan','duration'))
        if (not all(math.isfinite(x) for x in (beat,pitch,gain,pan,duration)) or
            not 0<=beat<256 or not 0<=pitch<=100 or not 0<=gain<=.3 or
            not -1<=pan<=1 or not 0<duration<=8 or row['kind'] not in KINDS):
            raise ValueError('Invalid music note')
        if row['kind']=='drum' and pitch not in range(6):raise ValueError('Invalid percussion')
        events.append(songs.Note(round(beat*songs.BEAT*songs.RATE),row['kind'],int(pitch),gain,pan,duration))
    events.sort(key=lambda event:event.start)
    info=song_info(seed,number*4)
    return songs.Song(info['title'],data['key'],(),tuple(events),tuple(e.start for e in events),(seed+number)%64)

@lru_cache(maxsize=128)
def instrument(kind,note,duration):
    if kind=='warmbed':return songs.warm_instrument(kind,note,duration)
    if kind in ('dustkeys','tapepiano','softorgan'):return recorded_piano(kind,note,duration)
    rate=songs.RATE
    duration=min(8,float(duration)+.8)
    t=np.arange(round(duration*rate),dtype=np.float64)/rate
    hz=440*2**((note-69)/12);phase=2*np.pi*hz*t
    if kind=='roundbass':
        body=np.sin(phase)+.30*np.sin(2*phase)*np.exp(-t*2.3)+.08*np.sin(3*phase)*np.exp(-t*5)
        env=(1-np.exp(-t*65))*np.exp(-t*1.3)
    else:raise ValueError('Unknown music instrument')
    dry=np.tanh(body*.85)*env*np.clip((duration-t)/.25,0,1)
    if kind!='roundbass':
        # Fixed short reflections and tremolo stay deterministic at WAV joins.
        dry*=.96+.04*np.sin(2*np.pi*2.3*t)
        wet=dry.copy()
        for delay,gain in ((.061,.12),(.127,.07),(.253,.04)):
            offset=round(delay*rate)
            if offset<len(dry):wet[offset:]+=dry[:-offset]*gain
        dry=wet
    return (dry*.9).astype(np.float32)

def samples(start,count,seed):
    if not count:return np.empty((0,2),dtype=np.float32)
    base=start//2;last=(start+count-1)//2+1
    low=songs._render(base,last-base+1,seed,composer=compose,voice_factory=instrument)
    positions=np.arange(count)+start%2;i=positions//2;blend=(positions%2).astype(np.float32)*.5
    return low[i]*(1-blend[:,None])+low[i+1]*blend[:,None]

def song_info(seed,phrase):
    number=phrase//4
    def title(n):
        index=(seed+n*37)%(len(songs.PLACES)*len(songs.TIMES))
        return f'{songs.PLACES[index%len(songs.PLACES)]} {songs.TIMES[index//len(songs.PLACES)]}'
    key=songs.KEYS[(seed+number*3)%len(songs.KEYS)]
    return {'number':number+1,'title':title(number),'next_title':title(number+1),
        'key':songs.KEY_NAMES[key]+' major / relative minor','duration_seconds':songs.SONG_FRAMES/48000,
        'section':' / '.join(songs.SECTIONS[(phrase%4)*2:(phrase%4)*2+2]),'phrase_in_song':phrase%4+1,
        'palette':PALETTES[number%3],'engine':'Strudel 1.2.6 / CC0 upright piano and original rhythm section'}



@lru_cache(maxsize=20)
def piano_source(note):
    import wave
    folder=Path(__file__).parent/'assets/piano-kw'
    with wave.open(str(folder/f'{note}.wav'),'rb') as wav:
        if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,24000):
            raise ValueError('Invalid piano recording')
        return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768

@lru_cache(maxsize=128)
def recorded_piano(kind,note,duration):
    from scipy.signal import butter,sosfilt
    # Prepared CC0 soft-velocity notes span C2 to C6 in minor thirds.
    centre=min(range(36,85,3),key=lambda n:abs(n-note))
    source=piano_source(centre)
    duration=min(8,float(duration)+.8)
    t=np.arange(round(duration*songs.RATE),dtype=np.float64)/songs.RATE
    indices=t*songs.RATE*2**((note-centre)/12)
    audio=np.interp(indices,np.arange(len(source)),source,left=0,right=0)
    cutoff={'dustkeys':2200,'tapepiano':3400,'softorgan':1500,'hifipiano':8200}[kind]
    audio=sosfilt(butter(2,cutoff,fs=songs.RATE,output='sos'),audio)
    audio*=np.clip(t/.006,0,1)*np.clip((duration-t)/.65,0,1)
    if kind!='hifipiano':audio*=.97+.03*np.sin(2*np.pi*2.1*t)
    dry=audio.copy()
    for delay,gain in ((.079,.13),(.173,.07)):
        offset=round(delay*songs.RATE)
        if offset<len(audio):audio[offset:]+=dry[:-offset]*gain
    if kind=='hifipiano':return (audio*1.44).astype(np.float32)
    return (np.tanh(audio*1.6)*.9).astype(np.float32)
