"""Versioned deployment settings; operator scene settings remain in the data root."""
import json
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)


class Location(Strict):
    name:str=Field(default='Local area',min_length=1,max_length=80)
    latitude:float=Field(default=0,ge=-90,le=90)
    longitude:float=Field(default=0,ge=-180,le=180)
    timezone:str='UTC'
    clock_label:str=Field(default='',max_length=24)
    @field_validator('timezone')
    @classmethod
    def timezone_known(cls,value):
        try:ZoneInfo(value)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('Unknown IANA timezone')
        return value


def endpoint(value,schemes):
    if not value:return value
    if any(ord(c)<33 or c in '"\\' for c in value):raise ValueError('Invalid endpoint characters')
    parsed=urlsplit(value)
    if parsed.scheme not in schemes or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError('Use a supported URL without embedded credentials')
    try:parsed.port
    except ValueError:raise ValueError('Invalid endpoint port')
    return value.rstrip('/')


class Inputs(Strict):
    camera_base:str='rtsp://192.0.2.10:8554'
    camera_shared_base:str='rtsp://source-hub:8554'
    camera_rtmp_base:str='rtmp://source-hub:1935'
    camera_hls_base:str='http://source-hub:8888'
    adsb_url:str=''
    metadata_url:str=''
    @field_validator('camera_base','camera_shared_base')
    @classmethod
    def camera_endpoint(cls,v):return endpoint(v,{'rtsp'})
    @field_validator('camera_rtmp_base')
    @classmethod
    def rtmp_endpoint(cls,v):return endpoint(v,{'rtmp','rtmps'})
    @field_validator('adsb_url','metadata_url','camera_hls_base')
    @classmethod
    def http_endpoint(cls,v):return endpoint(v,{'http','https'})


class Output(Strict):
    profile:Literal['720p3000','720p6000','1080p3000','1080i5994','2160p3000','2160p6000']='1080p3000'
    playout:bool=False
    amcp_host:str=Field(default='engine',pattern=r'^[A-Za-z0-9_.:-]{1,253}$')
    amcp_port:int=Field(default=5250,ge=1,le=65535)
    studio_url:str='http://studio:8765'
    @field_validator('studio_url')
    @classmethod
    def studio_endpoint(cls,v):return endpoint(v,{'http','https'})
    publish:bool=False
    publish_url:str=''
    encoder:Literal['h264_nvenc','libx264']='h264_nvenc'
    x264_preset:Literal['ultrafast','superfast','veryfast','faster','fast','medium']='veryfast'
    bitrate_kbps:int=Field(default=12000,ge=1000,le=80000)
    hdmi:bool=False
    headless:bool=False
    desktop_audio:bool=False
    screen:int=Field(default=0,ge=0,le=8)
    screen_rect:tuple[int,int,int,int]=(0,0,1920,1080)
    audio_rate:Literal[48000]=48000
    @model_validator(mode='after')
    def interlaced_encoder(self):
        if self.headless and (self.hdmi or self.desktop_audio):
            raise ValueError('Headless output cannot use HDMI windows or desktop audio; disable those outputs')
        if self.profile=='1080i5994' and self.publish and self.encoder!='libx264':
            raise ValueError('Interlaced publishing currently requires libx264')
        return self
    @field_validator('publish_url')
    @classmethod
    def publish_endpoint(cls,v):return endpoint(v,{'rtmp','rtmps','srt','udp'})
    @field_validator('screen_rect')
    @classmethod
    def bounded_rect(cls,v):
        if not all(-16384<=x<=16384 for x in v[:2]) or not all(320<=x<=8192 for x in v[2:]):raise ValueError('Invalid screen rectangle')
        return v


class Storage(Strict):
    cache_mib:int=Field(default=2048,ge=128,le=65536)
    history_days:int=Field(default=30,ge=1,le=365)
    minimum_free_mib:int=Field(default=2048,ge=512,le=65536)


PROVIDERS=('adsb','metadata','news','weather','flights','markets','marine','ais','tides','outages','power','power_reports','alerts','radar')


class StationConfig(Strict):
    schema_version:Literal[1]=1
    location:Location=Field(default_factory=Location)
    regional_preset:Literal['none','newfoundland']='none'
    inputs:Inputs=Field(default_factory=Inputs)
    output:Output=Field(default_factory=Output)
    storage:Storage=Field(default_factory=Storage)
    data_directory:str='data'
    music_directory:str='music'
    brand_file:str=''
    secrets_directory:str='secrets'
    secrets:dict[str,str]=Field(default_factory=dict)
    providers:dict[str,bool]=Field(default_factory=lambda:{k:False for k in PROVIDERS})
    @field_validator('providers')
    @classmethod
    def known_providers(cls,v):
        if set(v)-set(PROVIDERS):raise ValueError('Unknown provider group')
        return {k:v.get(k,False) for k in PROVIDERS}
    @field_validator('secrets')
    @classmethod
    def secret_names(cls,v):
        import re
        if set(v)-{'aisstream','finnhub','aeroapi','publish_url'}:raise ValueError('Unknown secret role')
        if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',name) or name in ('.','..') for name in v.values()):
            raise ValueError('Secrets must be filenames inside the secrets directory')
        return v

    @model_validator(mode='after')
    def provider_scope(self):
        regional={'weather','flights','marine','tides','outages','power','power_reports','radar'}
        if self.regional_preset=='none' and any(self.providers.get(k) for k in regional):
            raise ValueError('These adapters require the explicitly selected Newfoundland regional preset')
        if self.output.publish and not (self.output.publish_url or self.secrets.get('publish_url')):
            raise ValueError('Publishing requires a destination or publish_url secret reference')
        return self


def load(path):
    p=Path(path)
    if p.stat().st_size>256_000:raise ValueError('Station configuration exceeds 256 KB')
    try:return StationConfig.model_validate_json(p.read_text(encoding='utf-8'))
    except ValueError as exc:
        # Pydantic diagnostics may include submitted values. Never echo them.
        raise ValueError('Invalid station configuration; check schema version, field names, ranges and secret references') from None


CONFIG_PATH=Path(os.environ['STATION_CONFIG']).resolve() if os.environ.get('STATION_CONFIG') else None
CONFIG=load(CONFIG_PATH) if CONFIG_PATH else StationConfig()


def resolve_path(value):
    path=Path(value)
    return path if path.is_absolute() else (CONFIG_PATH.parent if CONFIG_PATH else Path(__file__).parents[1])/path


def secret(role):
    if os.environ.get('STATION_OFFLINE','1')!='0':return ''
    name=CONFIG.secrets.get(role)
    if not name:return ''
    root=resolve_path(CONFIG.secrets_directory).resolve();path=root/name
    if path.is_symlink() or path.resolve().parent!=root:raise ValueError('Secret path is not a regular local file')
    if path.stat().st_size>8192:raise ValueError('Secret file is too large')
    if os.name!='nt' and path.stat().st_mode & 0o077:raise ValueError('Secret file must be accessible only to its owner')
    value=path.read_text().strip()
    if not value or any(ord(c)<32 for c in value):raise ValueError('Secret file must contain a single nonempty line')
    return value


def provider_enabled(name):return CONFIG.providers.get(name,False)


def bootstrap():
    if CONFIG_PATH:
        os.environ.setdefault('SKYCAM_DATA',str(resolve_path(CONFIG.data_directory)))
        os.environ.setdefault('SKYCAM_MUSIC',str(resolve_path(CONFIG.music_directory)))
        if CONFIG.brand_file:os.environ.setdefault('STATION_BRAND_FILE',str(resolve_path(CONFIG.brand_file)))
        os.environ.setdefault('SKYCAM_FEED',CONFIG.inputs.adsb_url)
        os.environ.setdefault('SKYCAM_METADATA_BASE',CONFIG.inputs.metadata_url)
        os.environ.setdefault('SKYCAM_PLAYOUT','1' if CONFIG.output.playout else '0')
    # Online mode is an explicit deployment switch, never inherited from an import.
    os.environ.setdefault('STATION_OFFLINE','1')


def clock_label():
    return CONFIG.location.clock_label or ('NEWFOUNDLAND' if CONFIG.location.timezone=='America/St_Johns' else CONFIG.location.timezone.rsplit('/',1)[-1].replace('_',' ').upper())
