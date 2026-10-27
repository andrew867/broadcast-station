"""One coordinated, backed-up application of the station's default format."""
import hashlib,json,time,copy
from pathlib import Path
from pydantic import Field
from .models import StrictModel
from .rundown import RundownConfig
from .rundown_library import LibraryWrite,LibraryConflict
from .program_clock import ClockConfig,ClockRule,ClockWrite
from .storage import save_json

BLOCKS={
 'Electricity update':[('power-supply',25),('power-history',30),('power-report',35)],
 'Power outage update':[('power-outages',60)],
 'Short local forecast':[('weather',35),('radar-east',25)],
 'Extended local weather':[('weather',45),('radar-east',35),('radar-island',35),('daylight',25)],
 'Local information':[('yyt-arrivals',45),('yyt-departures',45),('marine',80),('tides',25),('moon',25),('markets',25),('power-supply',25)],
}
def block_config(name):return RundownConfig(cues=[{'camera':c,'seconds':s} for c,s in BLOCKS[name]])
def fingerprint(config):return hashlib.sha256(config.model_dump_json().encode()).hexdigest()
def presets():return json.loads((Path(__file__).parent/'static/rundown-presets.json').read_text())
class FormatWrite(StrictModel):
    preset_id:str
    expected_rundown_hash:str
    expected_clock_revision:int=Field(ge=0)
    expected_library_revision:int=Field(ge=0)

def public(rundown,clock,library):return {'presets':presets(),'rundown_hash':fingerprint(rundown.config),'clock_revision':clock.revision,'library_revision':library.public()['revision']}

def apply(data,rundown,clock,library,body):
    preset=next((r for r in presets() if r['id']==body.preset_id),None)
    if not preset:raise ValueError('Unknown background format')
    config=RundownConfig(cues=preset['cues'],transition=preset['transition'],resume_after_restart=True)
    from .playout import available
    if any(not available(c.camera) for c in config.cues):raise ValueError('The format contains an unavailable scene')
    with rundown.lock,clock.lock,library.lock:
        if fingerprint(rundown.config)!=body.expected_rundown_hash or clock.revision!=body.expected_clock_revision or library.public()['revision']!=body.expected_library_revision:raise LibraryConflict('Rundown, clock or library changed. Reload before applying a format.')
        saved={'rundown':rundown.public(),'clock':clock.public(),'library':library.document.model_dump(),'saved_at':time.time()}
        backup=data/'broadcast'/'format-backups'/('format-'+str(time.time_ns())+'.json');save_json(backup,saved)
        missing=sum(not any(i['name']==name for i in library.public()['items']) for name in BLOCKS)
        if len(library.public()['items'])+missing>50:raise ValueError('Free library space for the default blocks before applying')
        if any(not available(c.camera) for name in BLOCKS for c in block_config(name).cues):raise ValueError('A default block contains an unavailable scene')
        old_document=copy.deepcopy(library.document);old_clock=(clock.config,clock.revision,clock.armed_at)
        old_rundown={k:copy.deepcopy(getattr(rundown,k)) for k in ('config','enabled','index','deadline','error','note','block','block_index','clock_preview','interlude','followup_queue','resume_pending','prepared_index')}
        ids={}
        try:
            for name in BLOCKS:
                doc=library.public();old=next((i for i in doc['items'] if i['name']==name),None)
                ids[name]=library.save(LibraryWrite(name=name,config=block_config(name),expected_revision=doc['revision']),old['id'] if old else None)['saved_id']
            clock.save(ClockWrite(expected_revision=clock.revision,config=ClockConfig(enabled=True,rules=[
                ClockRule(id='short-weather',playlist_id=ids['Short local forecast'],every_minutes=10,priority=10),
                ClockRule(id='extended-weather',playlist_id=ids['Extended local weather'],every_minutes=20,priority=20,include_alerts=True),
                ClockRule(id='power-outages',playlist_id=ids['Power outage update'],every_minutes=15,offset_minutes=13,priority=5,condition='power-outages'),
                ClockRule(id='local-information',playlist_id=ids['Local information'],every_minutes=30,offset_minutes=5,priority=1),
            ])))
            rundown.save(config);rundown.action('start')
        except Exception:
            library.document=old_document;clock.config,clock.revision,clock.armed_at=old_clock
            for key,value in old_rundown.items():setattr(rundown,key,value)
            save_json(library.path,old_document.model_dump())
            save_json(clock.path,{'revision':clock.revision,'config':clock.config.model_dump()})
            save_json(rundown.path,rundown.config.model_dump());rundown._persist_intent()
            raise
        return {'name':preset['name'],'backup':str(backup),'rundown':rundown.public(),'clock':clock.public()}
