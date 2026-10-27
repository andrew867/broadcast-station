"""Startup-loaded identity, separate from stable package/API identifiers."""
import hashlib
import html
import json
import os
import re
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator
from fastapi.responses import HTMLResponse


class Branding(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    product_name:str=Field(default='Station',min_length=1,max_length=48)
    station_name:str=Field(default='Demo Station',min_length=1,max_length=80)
    station_short:str=Field(default='STATION',min_length=1,max_length=24)
    tagline:str=Field(default='',max_length=100)
    website:str=Field(default='',max_length=100)
    accent:str=Field(default='#ed6a36',pattern=r'^#[0-9a-fA-F]{6}$')
    logo_asset:str=Field(default='',max_length=100)

    @field_validator('product_name','station_name','station_short','tagline','website')
    @classmethod
    def printable(cls,value):
        if any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('Brand text must be a single line')
        if value and not value.strip():raise ValueError('Brand text cannot be whitespace only')
        return value

    @field_validator('logo_asset')
    @classmethod
    def local_logo(cls,value):
        if value and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:png|jpg|jpeg)',value):
            raise ValueError('Logo must be a local PNG/JPEG filename, without folders')
        return value

    def fingerprint(self):
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:16]


CONFIG_PATH=Path(os.environ['STATION_BRAND_FILE']) if os.environ.get('STATION_BRAND_FILE') else None
BRAND=Branding.model_validate_json(CONFIG_PATH.read_text(encoding='utf-8')) if CONFIG_PATH else Branding()


def logo_path():
    if not BRAND.logo_asset or CONFIG_PATH is None:return None
    folder=(CONFIG_PATH.parent/'branding-assets').resolve()
    path=(folder/BRAND.logo_asset).resolve()
    if path.parent!=folder or not path.is_file() or path.stat().st_size>2_000_000:
        raise ValueError('Brand logo missing, outside its folder or larger than 2 MB')
    from PIL import Image
    with Image.open(path,formats=('PNG','JPEG','WEBP')) as im:
        if im.width>4096 or im.height>4096:raise ValueError('Brand logo dimensions exceed 4096 pixels')
        im.verify()
    return path


def branded_html(path):
    text=Path(path).read_text(encoding='utf-8')
    for name,value in BRAND.model_dump().items():
        text=text.replace('[['+name+']]',html.escape(value,quote=True))
    return HTMLResponse(text)
