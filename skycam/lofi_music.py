"""Original 909-inspired synthesized one-shots, mellow keys and a changing bass groove.

No Roland recordings or external sample library. Small cached kits are sampled
at absolute musical positions, preserving deterministic block boundaries.
"""
from functools import lru_cache
import numpy as np

RATE=48000
BPM=78
def variation(seed,section):
    x=np.asarray(section,dtype=np.int64)+int(seed)*2654435761
    x=((x^(x>>16))&0x7fffffff)*73244475
    return (x^(x>>13))&0x7fffffff

@lru_cache(maxsize=8)
def kit(seed,rate=RATE):
    rng=np.random.default_rng(seed);t=np.arange(rate,dtype=np.float64)/rate
    noise=rng.uniform(-1,1,len(t));smooth=np.convolve(noise,np.ones(9)/9,'same')
    attack=1-np.exp(-t*1800)
    kick=np.sin(2*np.pi*(47*t+3.4*(1-np.exp(-t*36))))*np.exp(-t*12)*attack
    snare=(.45*np.sin(2*np.pi*178*t)*np.exp(-t*23)+smooth*2.8*np.exp(-t*18))*attack
    clap=smooth*(np.exp(-t*45)+np.exp(-np.maximum(t-.012,0)*45)*(t>=.012)+np.exp(-np.maximum(t-.026,0)*25)*(t>=.026))*attack
    metal=sum(np.sin(2*np.pi*f*t) for f in (331,475,634,811,1031,1439))/6
    closed=(noise*.2+metal*.8)*np.exp(-t*110)*attack
    opened=(noise*.12+metal*.8)*np.exp(-t*17)*attack
    rim=(np.sin(2*np.pi*430*t)+.6*np.sin(2*np.pi*1010*t))*np.exp(-t*95)*attack
    return tuple(x.astype(np.float32) for x in (kick,snare,clap,closed,opened,rim))

@lru_cache(maxsize=64)
def keyboard(note,rate=RATE):
    """A warm original electric-keyboard one-shot, sampled rather than revoiced per block."""
    t=np.arange(rate*3,dtype=np.float64)/rate;f=440*2**((int(note)-69)/12)
    body=np.sin(2*np.pi*f*t+.32*np.exp(-t*7)*np.sin(2*np.pi*f*2.005*t))
    body+=.12*np.sin(2*np.pi*f*.998*t)+.08*np.sin(2*np.pi*f*3*t)*np.exp(-t*6)
    envelope=(1-np.exp(-t*190))*np.exp(-t*2.3)*np.clip((3-t)/.1,0,1)
    # Fixed low-pass and gentle saturation give the generated recording a softer attack.
    return np.convolve(np.tanh(body*1.15)*envelope,np.ones(13)/13,'same').astype(np.float32)

def _samples(start,count,seed,study=False,rate=RATE):
    t=(start+np.arange(count,dtype=np.float64))/rate;beat=60/(74 if study else BPM);b=t/beat
    swing=.60 if study else .56
    bars=np.floor(b/4).astype(np.int64);section=bars//8;v=variation(seed,section)
    progress=np.asarray(((48,53,57,55),(53,52,50,55),(48,57,50,55),(53,55,52,57),(50,55,48,53),(48,55,53,50)))
    chord=np.floor(b/8).astype(np.int64);age=np.mod(b,8)*beat
    root=progress[v%len(progress),chord%4]
    prevbar=bars-2;prevroot=progress[variation(seed,prevbar//8)%len(progress),((chord-1)%4)]
    blend=np.clip(age/.32,0,1);blend=blend*blend*(3-2*blend)
    left=np.zeros(count);right=np.zeros(count)
    # Warm extended chords with continuous oscillator phase and gentle stereo drift.
    for base,weight in ((root,blend),(prevroot,1-blend)):
        minor=np.isin(base,(50,52,57))
        for i,interval in enumerate((0,np.where(minor,3,4),7,np.where(minor,10,11),14)):
            hz=440*2**((base+12+interval-69)/12);phase=2*np.pi*hz*t
            gain=(.012 if study else .024)*weight
            left+=(np.sin(phase+.035*np.sin(t*1.7+i))+.11*np.sin(phase*2))*gain
            right+=(np.sin(phase+.035*np.sin(t*1.6+i+.4))+.11*np.sin(phase*2))*gain
    # Swing eighth notes without changing the master tempo.
    whole=np.floor(b).astype(np.int64);fraction=np.mod(b,1);late=fraction>=swing
    step=whole*2+late;onset=whole+late*swing;a=(b-onset)*beat
    duration=np.where(late,1-swing,swing)*beat
    gate=np.asarray(((1,0,1,0,0,1,1,0),(1,0,0,1,1,0,1,1),(1,0,1,1,0,1,0,1),(1,0,0,1,1,0,1,0)))[v%4,step%8]
    offsets=np.asarray(((0,0,0,7,0,12,7,0),(0,7,0,10,0,0,7,12),(0,0,7,0,12,7,0,0)))[(v//7)%3,step%8]
    f=440*2**((root-12+offsets-69)/12)
    env=(1-np.exp(-a*100))*np.exp(-a*2)*np.clip((duration-a)/.035,0,1)
    bass=(.12 if study else .105)*(np.sin(2*np.pi*f*a)+.20*np.sin(4*np.pi*f*a))*env*gate
    if study:
        # Sparse chord stabs and their tails, with laid-back offbeat placement.
        # Individual keys are original cached one-shots, no external recordings.
        for ago in (0,1,2):
            hit=np.floor((b-.10)/2).astype(np.int64)-ago
            on=hit*2+.10;aa=(b-on)*beat
            hv=variation(seed,np.floor(on/32).astype(np.int64))
            rr=progress[hv%len(progress),(np.floor(on/8).astype(np.int64))%4]
            mask=(hit>=0)&(aa>=0)&(aa<3)
            # Every fourth stab becomes a lighter answering chord.
            dynamics=np.where(hit%4==3,.60,1)
            minor=np.isin(rr,(50,52,57))
            idx=np.clip(np.rint(aa*rate).astype(np.int64),0,rate*3-1)
            for j,interval in enumerate((np.where(minor,3,4),7,np.where(minor,10,11),14)):
                notes=rr+12+interval;voice=np.zeros(count)
                for note in np.unique(notes):
                    selected=(notes==note)&mask
                    voice[selected]=keyboard(int(note),rate)[idx[selected]]
                pan=(-.3,.2,-.1,.35)[j];gain=.046*dynamics
                left+=voice*gain*(1-pan);right+=voice*gain*(1+pan)
    # Piano fills every beat, with small motifs selected afresh every eight bars.
    for delay,gain,pan in (() if study else ((0,.060,-.2),(.75,.023,.4))):
        bt=np.maximum(0,b-delay);st=np.floor(bt).astype(np.int64);pa=np.mod(bt,1)*beat
        rb=np.floor(bt/4).astype(np.int64);vv=variation(seed,rb//8)
        rr=progress[vv%len(progress),(st//8)%4]
        notes=np.asarray(((12,19,23,26,19,16,14,19),(24,19,16,14,12,19,23,26),(16,14,19,23,26,19,16,12),(19,26,23,19,14,16,19,24)))[(vv//11)%4,st%8]
        notes=np.where(np.isin(rr,(50,52,57))&np.isin(notes%12,(4,11)),notes-1,notes)
        f=440*2**((rr+notes-69)/12)
        e=(1-np.exp(-pa*80))*np.exp(-pa*3.5)*np.clip((beat-pa)/.045,0,1)
        voice=np.sin(2*np.pi*f*pa+.35*np.exp(-pa*7)*np.sin(4*np.pi*f*pa))*e*gain*(b>=delay)
        left+=voice*(1-pan);right+=voice*(1+pan)
    # Sample the original compact kit. Absolute positions keep noise repeatable across chunks.
    sounds=kit(seed%64,rate);drums=np.zeros(count)
    patterns=(
        ((1,0,0,0,0,1,0,0),(1,0,0,1,0,0,1,0),(1,0,0,0,1,0,0,1)),
        ((0,0,1,0,0,0,1,0),)*3,
        ((0,0,0,0,0,0,1,0),)*3,
        ((1,1,1,1,1,1,1,1),)*3,
        ((0,0,0,1,0,0,0,0),(0,0,0,0,0,0,0,1),(0,0,0,1,0,0,0,1)),
        ((0,0,0,0,0,1,0,0),(0,1,0,0,0,0,0,1),(0,0,0,1,0,1,0,0)))
    # Include the preceding step so open hats and snare tails survive the next onset.
    for ago in (0,1,2):
        st=step-ago;on=st//2+(st%2)*swing;aa=(b-on)*beat
        vv=variation(seed,st//16//4);variant=(vv//19)%3
        index=np.clip(np.rint(aa*rate).astype(np.int64),0,rate-1)
        for i,gain in enumerate((.20,.13,.035,.028,.022,.018) if study else (.115,.072,.022,.020,.017,.020)):
            gates=np.asarray(patterns[i])[variant,st%8]*(st>=0)*(aa<1)
            # Slightly quieter alternate hats and rotating rim fills.
            dynamics=(.65+.35*(st%2==0)) if i==3 else 1
            drums+=sounds[i][index]*gain*gates*dynamics
    mono=bass+drums
    fade=np.clip(t/.04,0,1)
    return (np.tanh(np.column_stack((left+mono,right+mono))*1.2)*.68*fade[:,None]).astype(np.float32)


def samples(start,count,seed,study=False):
    if not study:return _samples(start,count,seed)
    if count==0:return np.empty((0,2),dtype=np.float32)
    # The study palette is deliberately bandwidth-limited. Synthesize its warm
    # one-shots at24kHz, then interpolate absolute positions to the48kHz bus.
    # Include the following source sample so arbitrary block joins stay exact.
    base=start//2;last=(start+count-1)//2+1
    low=_samples(base,last-base+1,seed,True,24000)
    indices=np.arange(count)+(start%2);i=indices//2;blend=(indices%2).astype(np.float32)*.5
    return low[i]*(1-blend[:,None])+low[i+1]*blend[:,None]
