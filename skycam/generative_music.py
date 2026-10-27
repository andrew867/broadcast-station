"""Original, sample-free weather-channel synthesis, rendered in bounded PCM blocks.

No browser, model, external samples or GPU. Absolute sample positions make
adjacent phrases continuous even when rendered separately or after a reload.
"""
from .public_errors import public_error
import math,time,wave,hashlib
from pathlib import Path
import numpy as np

RATE=48000
MOODS={'radio':{'name':'Rainlight Study Radio','bpm':80},'strudel':{'name':'Strudel Study Radio','bpm':74},'warm':{'name':'Velvet Study','bpm':74},'study':{'name':'Late Study','bpm':74},'lofi':{'name':'Mall Afterglow','bpm':78},'coastal':{'name':'Coastal FM','bpm':80},'night':{'name':'After Hours','bpm':64}}
PROGRESSIONS=[(48,53,50,55),(53,48,55,50),(50,55,48,53),(48,57,53,55)]

def samples(start,count,seed=247,mood='coastal',radio_options=None):
    """Return normalized float stereo PCM at an absolute sample offset."""
    if mood == 'radio':
        from .study_radio import samples as radio_samples
        return radio_samples(start,count,seed,radio_options)
    if mood == 'strudel':
        from .strudel_music import samples as strudel_samples
        return strudel_samples(start,count,seed)
    if mood in ('study','warm'):
        from .study_songs import samples as song_samples
        return song_samples(start,count,seed,warm=mood=='warm')
    if mood == 'lofi':
        from .lofi_music import samples as lofi_samples
        return lofi_samples(start,count,seed,study=mood=='study')
    bpm=MOODS[mood]['bpm'];beat=60/bpm
    t=(start+np.arange(count,dtype=np.float64))/RATE
    b=t/beat;bar=np.floor(b/4).astype(np.int64);age=np.mod(b,4)*beat
    # Change the progression every sixteen bars, deterministically by seed.
    cycle=bar//16
    choices=(cycle*1103515245+seed*12345)%len(PROGRESSIONS)
    roots=np.asarray(PROGRESSIONS)[choices,(bar//2)%4]
    minor=(roots==50)|(roots==57)
    chord=np.floor(b/8).astype(np.int64);chordage=np.mod(b,8)*beat
    prevbar=bar-2;prevchoices=((prevbar//16)*1103515245+seed*12345)%len(PROGRESSIONS)
    previous=np.asarray(PROGRESSIONS)[prevchoices,(prevbar//2)%4]
    previous_minor=(previous==50)|(previous==57)
    left=np.zeros(count);right=np.zeros(count)
    blend=np.minimum(chordage/.8,1);blend=blend*blend*(3-2*blend)
    # Overlapping sustained chords: no empty interval at a bar boundary.
    for old,weight in ((False,blend),(True,1-blend)):
        base=previous if old else roots;is_minor=previous_minor if old else minor
        for i,offset in enumerate((0,np.where(is_minor,3,4),7,np.where(is_minor,10,11),14)):
            note=base+12+offset
            hz=440*2**((note-69)/12);phase=2*np.pi*hz*t
            gain=.029*weight*(.92+.08*np.sin(t*.13+i))
            voice=np.sin(phase+.18*np.sin(2*np.pi*.21*t+i))+.10*np.sin(2*phase)
            left+=voice*gain*(.9+.1*math.cos(i))
            right+=(np.sin(phase+.18*np.sin(2*np.pi*.19*t+i))+.10*np.sin(2*phase))*gain*(.9-.1*math.cos(i))
    # Electric-piano motif, with two analytic echo taps and a slow evolving rest.
    for delay,gain,pan in ((0,.075,-.25),(.52,.026,.45),(1.04,.015,-.55)):
        bt=(t-delay)/beat;step=np.floor(bt).astype(np.int64);a=np.mod(bt,1)*beat
        rbar=np.floor(bt/4).astype(np.int64);rchoose=((rbar//16)*1103515245+seed*12345)%len(PROGRESSIONS)
        root=np.asarray(PROGRESSIONS)[rchoose,(rbar//2)%4]
        variant=(step//32+seed)%4
        motif=np.asarray(((12,19,23,26,19,16,14,19),(19,16,14,12,26,23,19,14),(24,19,16,14,12,19,23,26),(16,19,26,23,19,14,16,12)))[variant,(step+seed)%8]
        motif=np.where(((root==50)|(root==57))&((motif%12==4)|(motif%12==11)),motif-1,motif)
        f=440*2**((root+motif-69)/12)
        env=(1-np.exp(-a*45))*np.exp(-a*2.7)*np.minimum((beat-a)/.06,1)
        gate=((step+seed+step//32)%8!=7)&(bt>=0)
        voice=np.sin(2*np.pi*f*a+.45*np.exp(-a*5)*np.sin(2*np.pi*f*2*a))*env*gate*gain
        left+=voice*(1-pan);right+=voice*(1+pan)
    # Rounded bass, sparse kick, brushed snare and very soft hats.
    ba=np.mod(b,2)*beat
    f=440*2**((roots-12-69)/12)
    bass=.085*np.sin(2*np.pi*f*ba)*(1-np.exp(-ba*80))*np.exp(-ba*1.5)*np.minimum((2*beat-ba)/.05,1)
    kickage=np.mod(b,2)*beat
    kick=.09*np.sin(2*np.pi*(46*kickage+3*(1-np.exp(-kickage*30))))*np.exp(-kickage*17)
    noise=np.mod(np.sin((start+np.arange(count))*12.9898+seed)*43758.5453,1)*2-1
    snareage=np.mod(b-1,2)*beat
    snare=.018*noise*np.exp(-snareage*25)*(1-np.exp(-snareage*300))
    hatage=np.mod(b,.5)*beat
    hats=.006*noise*np.exp(-hatage*95)*(1-np.exp(-hatage*700))
    rhythm=(.32 if mood=='night' else .48)*(.8+.2*np.cos((bar//8)*1.7))
    mono=bass+rhythm*(kick+snare+hats)
    # Fixed soft limiter and initial fade only, never a fade between phrases.
    fade=np.minimum(t/2,1)
    return (np.tanh(np.column_stack((left+mono,right+mono))*1.25)*.68*fade[:,None]).astype(np.float32)

class Generator:
    def __init__(self,folder,radio_options=None):
        from .study_radio_config import StudyRadioConfig
        self.radio_options=StudyRadioConfig.model_validate(radio_options or {}).model_dump()
        import json
        self.radio_id=hashlib.sha256(json.dumps(self.radio_options,sort_keys=True).encode()).hexdigest()[:12]
        self.folder=Path(folder);self.last_render_seconds=None;self.error=None
    def bpm(self,mood):return self.radio_options['bpm'] if mood=='radio' else MOODS[mood]['bpm']
    def length(self,mood):return round(16*4*60/self.bpm(mood)*RATE)
    def version(self,mood):return 'v4-radio2'+self.radio_id if mood=='radio' else 'v3' if mood=='strudel' else 'v1' if mood=='warm' else 'v4' if mood=='study' else 'v2'
    def name(self,seed,mood,index):return f'skygen-{self.version(mood)}-{seed}-{mood}-{index:08d}.wav'
    def index(self,name,seed,mood):
        prefix=f'skygen-{self.version(mood)}-{seed}-{mood}-'
        if name and name.startswith(prefix) and name.endswith('.wav'):
            try:return int(name[len(prefix):-4])
            except ValueError:pass
        return None
    def ensure(self,seed,mood,index):
        name=self.name(seed,mood,index);path=self.folder/name
        self.folder.mkdir(parents=True,exist_ok=True)
        if path.exists():return name
        began=time.monotonic();frames=self.length(mood);tmp=path.with_suffix('.tmp')
        try:
            with wave.open(str(tmp),'wb') as output:
                output.setnchannels(2);output.setsampwidth(2);output.setframerate(RATE)
                for offset in range(0,frames,RATE):
                    audio=samples(index*frames+offset,min(RATE,frames-offset),seed,mood,self.radio_options)
                    output.writeframesraw(np.rint(np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
            tmp.replace(path);self.last_render_seconds=round(time.monotonic()-began,3);self.error=None
            return name
        except Exception as exc:
            tmp.unlink(missing_ok=True);self.error=public_error(exc)[:160];raise
    def prune(self,keep):
        for path in self.folder.glob('skygen-v*-*.wav'):
            if path.name not in keep:path.unlink(missing_ok=True)
