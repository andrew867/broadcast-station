"""Independent, bounded alert presentation clock. Does not change program scenes.

Repeat intervals are station policy, not a regulatory compliance claim.
"""
from .public_errors import public_error
import hashlib
import json
import math
import threading
import time
from pydantic import Field
from .models import StrictModel
from .storage import save_json
from .alert_graphics import emergency_rows, identity, body
from .outages import restoration, customer_text, is_planned
from .language_policy import english


class PresentationConfig(StrictModel):
    repeat_minutes: int = Field(default=10, ge=2, le=60)
    page_seconds: int = Field(default=22, ge=12, le=45)
    audio_enabled: bool = True
    audio_volume: float = Field(default=.65, ge=0, le=1)


def utility_alert(row, now):
    count = customer_text(row)
    text = (f"Power outage: {row['location']}. "
            + (count+". " if count else "") +
            f"Estimated restoration: {restoration(row, now)}. Cause: {row['cause']}. "
            + ('Crew: '+row['crew']+'. ' if row.get('crew') else '') + row.get('remarks', ''))
    return dict(sender=row.get('provider','Newfoundland Power'), sender_name=row.get('provider','Newfoundland Power'),
                identifier=row['id'], sent=row['start'], expires=0,
                areas=[row['location']], event='Power outage update', headline=row['location'],
                description=text, broadcast_text=text, language='en-CA', utility=True,
                restoration_summary='Est. restoration: '+restoration(row,now))

def read_times(path):
    """Presentation history is diagnostic state, never a reason to lose alerts."""
    try:
        if path.stat().st_size>1_000_000:raise ValueError('History exceeds size limit')
        data=json.loads(path.read_text())
        if not isinstance(data,dict):raise ValueError('History must be a mapping')
        ceiling=time.time()+60
        rows={k:v for k,v in data.items() if isinstance(k,str) and len(k)<=2000
              and type(v) in (int,float) and math.isfinite(v) and 0<=v<=ceiling}
        return dict(sorted(rows.items(),key=lambda row:row[1])[-512:])
    except (ValueError,OSError):return {}


class AlertPresentation:
    def __init__(self, data, alerts, outages, audio=None):
        self.path=data/'broadcast'/'alert-presentation.json'
        self.history_path=data/'broadcast'/'alert-presentation-history.json'
        self.message_history_path=data/'broadcast'/'alert-message-history.json'
        self.lock=threading.RLock(); self.alerts=alerts; self.outages=outages; self.audio=audio
        self.config=PresentationConfig.model_validate_json(self.path.read_text()) if self.path.exists() else PresentationConfig()
        self.completed=read_times(self.history_path)
        self.current=None; self.started=0.; self.rows=[]; self.status={}
        self.presented=read_times(self.message_history_path)
        self.token=0; self.audio_started=False

    def save(self, config):
        with self.lock:
            save_json(self.path,config.model_dump());self.config=config
            if not config.audio_enabled:self.stop_audio()

    def candidates(self, now):
        data=self.alerts(); items=[]
        # English station output only, also guard callers supplying older state.
        for a in sorted(data.get('immediate', []), key=lambda a:(a.get('received_at',0),a['sent'],a.get('language','en').startswith('fr'))):
            if not english(a.get('language')):continue
            key='cap-'+identity(a)
            # A minor update inherits the completed presentation time only for
            # a reference and language actually presented on this station.
            if a.get('minor_update') and key not in self.completed:
                dates=[self.presented.get(self.message_key(r,a.get('language','en')),0)
                       for r in a.get('references',[]) if r[0]==a['sender']]
                if dates and all(dates):self.completed[key]=max(dates)
            items.append(dict(key=key,alert=a,kind='emergency',fresh=data.get('fresh',False),interval=self.config.repeat_minutes*60))
        d=self.outages() if self.outages else {}
        if d.get('fresh') and d.get('config',{}).get('banner_enabled',False):
            for row in d.get('active',[]):
                if is_planned(row) or not row.get('fresh',True):continue
                key='utility-'+hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()[:24]
                items.append(dict(key=key,alert=utility_alert(row,now),kind='utility',fresh=True,interval=d['config']['repeat_minutes']*60))
        return items

    def stop_audio(self):
        if self.audio:self.audio.stop()
        self.audio_started=False

    @staticmethod
    def message_key(reference,language):
        return json.dumps([*reference,language],separators=(',',':'))

    def finish(self, now, completed=True):
        self.stop_audio()
        if self.current and completed:
            self.completed[self.current['key']]=now
            self.completed=dict(sorted(self.completed.items(),key=lambda p:p[1])[-512:])
            save_json(self.history_path,self.completed)
            a=self.current['alert']
            if self.current['kind']=='emergency':
                self.presented[self.message_key([a['sender'],a['identifier'],a['sent']],a.get('language','en'))]=now
                self.presented=dict(sorted(self.presented.items(),key=lambda p:p[1])[-512:])
                save_json(self.message_history_path,self.presented)
        self.current=None;self.rows=[]

    def frame(self, now=None):
        now=time.time() if now is None else now
        with self.lock:
            items=self.candidates(now);lookup={c['key']:c for c in items}
            if self.current:
                # Cancellation/expiry removes graphics and voice immediately.
                # Utility speech yields to official emergency information.
                a=self.current['alert'];reference=[a['sender'],a['identifier'],a['sent']]
                replacement=any(c['alert'].get('message_type')=='Update' and reference in [list(x) for x in c['alert'].get('references',[])] for c in items)
                removed=self.current['key'] not in lookup and not (replacement and a['expires']>now)
                if removed or (self.current['kind']=='utility' and any(c['kind']=='emergency' for c in items)):
                    self.finish(now,False)
                elif self.current['key'] in lookup:self.current['fresh']=lookup[self.current['key']]['fresh']
            if self.current:
                duration=len(self.rows)*self.config.page_seconds
                audio_info=self.audio.public() if self.audio else {}
                if self.config.audio_enabled and self.audio and not self.audio_started:
                    self.audio.prepare(self.current['key'],self.current['alert'])
                    if self.audio.ready(self.current['key']):
                        if self.audio.play(self.current['key'],self.config.audio_volume) is not False:
                            self.audio_started=True;self.started=now
                    elif now-self.started<60:
                        # Visual content starts immediately while speech is prepared.
                        duration=max(duration,61)
                if self.audio_started:duration=max(duration,audio_info.get('duration',0)+1)
                if now-self.started>=duration:
                    complete=True
                    if self.audio_started and hasattr(self.audio,'complete'):
                        try:complete=self.audio.complete()
                        except Exception as exc:self.audio.error=public_error(exc)[:240];complete=False
                        # A dead producer must not leave music muted indefinitely.
                        if not complete and now-self.started>duration*2+30:
                            self.audio.error='Alert audio exceeded its playback deadline; music restored'
                            complete=True
                    if complete:self.finish(now)
            if self.current is None:
                due=[c for c in items if now-self.completed.get(c['key'],-1e12)>=c['interval']]
                # While any official notice is active, utility notices wait.
                if any(c['kind']=='emergency' for c in items):due=[c for c in due if c['kind']=='emergency']
                if due:
                    self.current=due[0];self.rows=emergency_rows([self.current['alert']]);self.started=now;self.token+=1
                    if self.audio and self.config.audio_enabled:
                        self.audio.prepare(self.current['key'],self.current['alert'])
            if self.current:
                duration=len(self.rows)*self.config.page_seconds
                if self.audio_started and self.audio:duration=max(duration,self.audio.public().get('duration',0)+1)
                page=min(len(self.rows)-1,int((now-self.started)/max(1,duration/len(self.rows))))
                result=dict(mode='full',row=self.rows[page],kind=self.current['kind'],fresh=self.current['fresh'],key=self.current['key'],token=self.token)
            elif items:
                preferred=[c for c in items if c['kind']=='emergency'] or items
                selected=preferred[int(now//12)%len(preferred)]
                due=min(self.completed.get(c['key'],now)+c['interval'] for c in preferred)
                result=dict(mode='summary',row={'alert':selected['alert']},kind=selected['kind'],fresh=selected['fresh'],key=selected['key'],countdown=max(0,math.ceil(due-now)))
            else:result=None
            self.status={'config':self.config.model_dump(),'state':result['mode'] if result else 'idle',
                         'kind':result['kind'] if result else None,'countdown':result.get('countdown') if result else None,
                         'active_messages':len(items),'audio':self.audio.public() if self.audio else {'available':False},
                         'repeat_policy':'Station policy, not a prescribed NPAS repeat interval'}
            return result

    def public(self):
        with self.lock:return {**self.status,'config':self.config.model_dump()}
