"""Bounded local speech preparation, separate from the program music clock."""
from .public_errors import public_error
import hashlib
import json
import shutil
import subprocess
import time
import wave
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from .alert_graphics import body
from .alert_resources import supplied_audio
from .storage import save_json
from . import playout
from .language_policy import english


class AlertAudio:
    def __init__(self, data, music):
        self.folder=data/'runtime'/'alert-audio';self.folder.mkdir(parents=True,exist_ok=True)
        self.history_path=data/'broadcast'/'alert-audio-history.json'
        self.signal=Path(__file__).parent/'assets'/'attention.wav'
        self.music=music;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='alert-speech')
        self.job=None;self.key=None;self.asset=None;self.duration=0;self.error=None;self.playing=False
        self.source='Local speech';self.resource_warning=None
        self.prepared_identity=None;self.first=False;self.initialized=False;self.announced={};self.available=bool(shutil.which('espeak-ng'))
        try:self.announced=json.loads(self.history_path.read_text())
        except (ValueError,OSError):pass

    def recover(self):
        if self.initialized or not playout.STATUS.get('ready'):return
        with playout.LOCK:playout.command('CLEAR 1-6')
        self.music.ducked=True;self.music.set_duck(False);self.initialized=True

    def engine_lost(self):
        # No network commands while the engine is unavailable. Re-adopt and
        # restore its actual music gain before the next alert presentation.
        self.initialized=False;self.playing=False;self.music.ducked=False

    def public(self):
        return {'available':self.available,'preparing':bool(self.job and not self.job.done()),
                'playing':self.playing,'duration':self.duration,'error':self.error,
                'voice':self.source,'resource_warning':self.resource_warning,'attention_signal_available':self.signal.exists()}

    def prepare(self, key, alert):
        if not english(alert.get('language')):
            raise ValueError('Station alert speech is English only')
        identity=None if alert.get('utility') else hashlib.sha256(json.dumps([alert['sender'],alert['identifier'],alert['sent']]).encode()).hexdigest()
        first=identity is not None and identity not in self.announced
        if self.key==key and first==self.first:return
        # One outstanding job. A cancelled/expired alert can never be played by
        # its worker; all AMCP calls remain in the presentation thread.
        if self.job and not self.job.done():return
        self.key=key;self.asset=None;self.error=None;self.duration=0
        self.prepared_identity=identity;self.first=first
        self.job=self.pool.submit(self.render,key,alert,first)

    def render(self, key, alert, first):
        if not english(alert.get('language')):
            raise ValueError('Station alert speech is English only')
        target=self.folder/(key+'.wav');speech=self.folder/(key+'.speech.wav')
        # Exact supplied text, never generated or translated by a language model.
        text=body(alert)
        if not alert.get('broadcast_text'):
            text=' / '.join(alert['areas'])+'. '+text
        voice='en'
        try:
            audio,self.resource_warning=supplied_audio(alert,self.folder,key)
            self.source='Issuer supplied English audio' if audio is not None else 'Local English speech'
            if audio is None:
                if not self.available:raise RuntimeError('No usable supplied audio or local speech engine; visual presentation continues')
                subprocess.run(['espeak-ng','-v',voice,'-s','155','-w',str(speech),'--stdin'],input=text.encode('utf-8'),
                               stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True,timeout=45)
                with wave.open(str(speech),'rb') as f:
                    if f.getsampwidth()!=2 or f.getnchannels()!=1:raise ValueError('Unexpected speech format')
                    rate=f.getframerate();raw=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.float32)/32768
                if not 0<len(raw)<=rate*1200:raise ValueError('Speech duration outside supported limit')
                from math import gcd
                div=gcd(48000,rate);audio=resample_poly(raw,48000//div,rate//div)
            peak=float(np.max(np.abs(audio)))
            if peak>0:audio=audio*(.55/peak)
            if first:
                if not self.signal.exists():raise RuntimeError('Official attention signal missing; speech withheld, graphics continue')
                with wave.open(str(self.signal),'rb') as f:
                    if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(48000,1,2):raise ValueError('Unexpected attention signal format')
                    signal=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.float32)/32768
                audio=np.concatenate((signal,np.zeros(12000,dtype=np.float32),audio))
            tmp=target.with_suffix('.tmp')
            with wave.open(str(tmp),'wb') as f:
                f.setparams((2,2,48000,0,'NONE','not compressed'))
                f.writeframes(np.repeat(np.rint(np.clip(audio,-1,1)*32767).astype('<i2')[:,None],2,axis=1).tobytes())
            tmp.replace(target)
            for old in sorted(self.folder.glob('*.wav'),key=lambda p:p.stat().st_mtime)[:-12]:
                if old not in (target,speech):old.unlink(missing_ok=True)
            return target,len(audio)/48000
        finally:speech.unlink(missing_ok=True)

    def ready(self, key):
        if key!=self.key or not self.job or not self.job.done():return False
        if self.asset:return True
        try:self.asset,self.duration=self.job.result();return True
        except Exception as exc:self.error=public_error(exc)[:240];return False

    def play(self, key, volume):
        if not self.ready(key):return False
        self.music.set_duck(True)
        try:
            with playout.LOCK:
                playout.command(f'MIXER 1-6 VOLUME {volume}')
                playout.command(f'PLAY 1-6 "/workspace/runtime/alert-audio/{self.asset.name}"')
            self.playing=True
            if self.prepared_identity:
                self.announced[self.prepared_identity]=time.time()
                self.announced=dict(sorted(self.announced.items(),key=lambda p:p[1])[-512:])
                save_json(self.history_path,self.announced)
            return True
        except Exception:
            self.music.set_duck(False);raise

    def stop(self):
        if self.playing:
            try:
                with playout.LOCK:playout.command('CLEAR 1-6')
            finally:self.playing=False;self.music.set_duck(False)

    def complete(self):
        """Use the producer clock, so slow output does not truncate a message."""
        if not self.playing:return True
        with playout.LOCK:reply=playout.command('INFO 1',xml=True)
        node=ET.fromstring(reply[reply.index('<?xml'):]).find('.//layer_6/foreground')
        if node is None or node.findtext('producer')=='empty':return True
        if node.findtext('file/path','').rsplit('/',1)[-1]!=self.asset.name:
            raise RuntimeError('Alert audio producer changed unexpectedly')
        times=node.findall('file/time')
        return bool(times and float(times[0].text)>=self.duration-.08)
