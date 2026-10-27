"""Persistent camera inventory; IDs are independent of reserved playout channels."""
import json,os,threading,time
from pathlib import Path
from pydantic import Field,field_validator
from .models import StrictModel
from .map_scenes import MAP_SCENES,DIRECT_SCENES
from .source_routing import camera_base
from .station_config import CONFIG

CHANNELS=(4,5,6,7,9,10,11,12,13,14,15,16)
DEFAULT_QUAD_NAMES={'quad':'Camera group 1','quad2':'Camera group 2'}

class QuadSpec(StrictModel):
    id:str=Field(pattern=r'^(?:quad|quad2|quad-[a-z0-9][a-z0-9_-]{0,42})$')
    name:str=Field(min_length=1,max_length=64)
    cameras:list[str]=Field(min_length=4,max_length=4)
    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if not value or any(ord(c)<32 for c in value):raise ValueError('Use a visible single-line name')
        return value

class CameraSpec(StrictModel):
    id:str=Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,47}$')
    name:str=Field(min_length=1,max_length=64)
    location:str=Field(default=CONFIG.location.name,min_length=1,max_length=70)
    media_path:str=Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_/-]{0,127}$')
    width:int=Field(default=1920,ge=320,le=7680)
    height:int=Field(default=1080,ge=240,le=4320)
    enabled:bool=True
    attribution_enabled:bool=False
    attribution_text:str=Field(default='',max_length=100)
    @field_validator('id')
    @classmethod
    def reserved(cls,v):
        if v in {*MAP_SCENES,*DIRECT_SCENES,'quad','quad2'}:raise ValueError('This name belongs to a scene')
        return v
    @field_validator('name','location','attribution_text')
    @classmethod
    def printable(cls,v):
        if any(ord(c)<32 for c in v):raise ValueError('Use a single line of text')
        return v.strip()

class CameraRecord(CameraSpec):
    channel:int
    reference:str='camera-placeholder.svg'
    site_known:bool=False

def seed():
    ids=['cam1','cam2','cam3','cam4',*[f'ntv-cam{i}' for i in range(1,5)]]
    return [CameraRecord(id=id,name=f'Demo camera {i+1}',location='DEMONSTRATION / NOT LIVE',enabled=False,width=1280,height=720,reference='camera-reference.png',media_path=id,channel=CHANNELS[i],site_known=False).model_dump() for i,id in enumerate(ids)]


def enrich(row):
    base=camera_base(Path(os.environ.get('SKYCAM_DATA',Path(__file__).parent.parent/'data')))
    return {**row,'rtsp':base+'/'+row['media_path'],
            'rtmp':CONFIG.inputs.camera_rtmp_base+'/'+row['media_path'],
            'hls':CONFIG.inputs.camera_hls_base+'/'+row['media_path']+'/index.m3u8'}

class CameraCatalog:
    def __init__(self,data):
        self.path=data/'broadcast'/'cameras.json';self.lock=threading.RLock()
        saved=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'version':1,'cameras':seed(),'quads':{'quad':['cam1','cam2','cam3','cam4'],'quad2':[f'ntv-cam{i}' for i in range(1,5)]},'retired_ids':[]}
        if saved.get('version')!=1:raise ValueError('Unsupported camera registry version')
        rows=[CameraRecord.model_validate(r).model_dump() for r in saved['cameras']]
        if len({r['id'] for r in rows})!=len(rows) or len({r['channel'] for r in rows})!=len(rows) or any(r['channel'] not in CHANNELS for r in rows):raise ValueError('Duplicate camera ID or invalid decoder slot')
        self.cameras={r['id']:enrich(r) for r in rows};self.quads=saved['quads'];self.retired=saved.get('retired_ids',[])
        self.quad_names={id:saved.get('quad_names',{}).get(id,DEFAULT_QUAD_NAMES.get(id,id)) for id in self.quads}
        if not {'quad','quad2'}<=self.quads.keys() or len(self.quads)>12:raise ValueError('Invalid quad registry')
        for id,ids in self.quads.items():
            QuadSpec(id=id,name=self.quad_names[id],cameras=ids)
            if len(set(ids))!=4 or any(id not in self.cameras for id in ids):raise ValueError('Quad needs four different known cameras')
            if id in self.cameras:raise ValueError('Quad ID conflicts with a camera')
    def _write(self,cameras,quads,retired,quad_names=None):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        rows=[CameraRecord.model_validate({k:v for k,v in r.items() if k in CameraRecord.model_fields}).model_dump() for r in cameras.values()]
        names=dict(self.quad_names) if quad_names is None else quad_names
        payload={'version':1,'cameras':rows,'quads':quads,'quad_names':names,'retired_ids':retired}
        if self.path.exists():
            revisions=self.path.parent/'camera-revisions';revisions.mkdir(exist_ok=True)
            (revisions/f'{time.time_ns()}.json').write_bytes(self.path.read_bytes())
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(payload,indent=2),encoding='utf-8');temporary.replace(self.path)
        self.cameras.clear();self.cameras.update(cameras);self.quads.clear();self.quads.update(quads);self.retired=list(retired)
        self.quad_names.clear();self.quad_names.update(names)
    def initialize(self):
        with self.lock:
            if not self.path.exists():self._write(dict(self.cameras),dict(self.quads),list(self.retired))
    def public(self):
        with self.lock:return {'cameras':[dict(r) for r in self.cameras.values()],'quads':{k:list(v) for k,v in self.quads.items()},'quad_names':dict(self.quad_names),'quad_capacity':12,'capacity':len(CHANNELS)}
    def create(self,spec):
        with self.lock:
            if spec.id in self.cameras or spec.id in self.retired or spec.id in self.quads:raise ValueError('Camera ID already used; choose a new ID')
            free=[ch for ch in CHANNELS if ch not in {r['channel'] for r in self.cameras.values()}]
            if not free:raise ValueError('All configured decoder slots are assigned')
            row=enrich(CameraRecord(**spec.model_dump(),channel=free[0]).model_dump())
            self._write({**self.cameras,spec.id:row},dict(self.quads),self.retired)
            return row
    def update(self,id,spec):
        with self.lock:
            if id not in self.cameras or spec.id!=id:raise ValueError('Existing camera ID cannot be changed')
            row={**self.cameras[id],**spec.model_dump()};row=enrich(row)
            self._write({**self.cameras,id:row},dict(self.quads),self.retired);return row
    def delete(self,id):
        with self.lock:
            if id not in self.cameras:raise ValueError('Unknown camera')
            if any(id in ids for ids in self.quads.values()):raise ValueError('Remove this camera from its quad first')
            self._write({k:v for k,v in self.cameras.items() if k!=id},dict(self.quads),[*self.retired,id])
    def save_quad(self,id,cameras):
        with self.lock:
            if id not in self.quads or len(cameras)!=4 or len(set(cameras))!=4 or any(c not in self.cameras for c in cameras):raise ValueError('Choose four different known cameras')
            self._write(dict(self.cameras),{**self.quads,id:list(cameras)},self.retired)
    def write_quad(self,spec,create=False):
        with self.lock:
            if create and (spec.id in self.quads or spec.id in self.cameras or spec.id in self.retired):raise ValueError('Scene ID already used')
            if create and len(self.quads)>=12:raise ValueError('The library holds up to twelve quad scenes')
            if not create and spec.id not in self.quads:raise ValueError('Unknown quad scene')
            if len(set(spec.cameras))!=4 or any(c not in self.cameras for c in spec.cameras):raise ValueError('Choose four different known cameras')
            self._write(dict(self.cameras),{**self.quads,spec.id:list(spec.cameras)},self.retired,{**self.quad_names,spec.id:spec.name})
    def delete_quad(self,id):
        with self.lock:
            if id in DEFAULT_QUAD_NAMES:raise ValueError('Keep the two default quads; their membership and names can be edited')
            if id not in self.quads:raise ValueError('Unknown quad scene')
            self._write(dict(self.cameras),{k:v for k,v in self.quads.items() if k!=id},[*self.retired,id],{k:v for k,v in self.quad_names.items() if k!=id})

DATA=Path(os.environ.get('SKYCAM_DATA',Path(__file__).parent.parent/'data'))
CATALOG=CameraCatalog(DATA)
CAMERAS=CATALOG.cameras
QUADS=CATALOG.quads

def scene_rows():
    with CATALOG.lock:
        return [*CAMERAS.values(),*[{'id':id,'name':CATALOG.quad_names[id],'reference':CAMERAS[members[0]]['reference'],'location':'AVALON PENINSULA, NL','members':list(members)} for id,members in QUADS.items()],*[{'id':id,**meta,'reference':meta.get('reference','map-card.svg')} for id,meta in MAP_SCENES.items()],*[{'id':id,**meta} for id,meta in DIRECT_SCENES.items() if meta.get('kind')=='card']]
