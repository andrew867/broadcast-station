"""Saved map appearance with local astronomical sunrise/sunset switching."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import threading
from typing import Literal
from zoneinfo import ZoneInfo
from astral import Observer
from astral.sun import sunrise, sunset
from .models import StrictModel

# Existing station-area coordinates, independent of optical camera approval.
from .station_config import CONFIG
LATITUDE=CONFIG.location.latitude
LONGITUDE=CONFIG.location.longitude
TIMEZONE=CONFIG.location.timezone

class MapThemeRequest(StrictModel):
    mode: Literal['day','night','auto']='auto'
    show_info: bool=True

@lru_cache(maxsize=8)
def solar_events(date):
    observer=Observer(LATITUDE,LONGITUDE)
    tz=ZoneInfo(TIMEZONE)
    return sunrise(observer,date,tzinfo=tz),sunset(observer,date,tzinfo=tz)

class MapTheme:
    def __init__(self,data):
        self.path=data/'broadcast'/'map-theme.json'
        self.lock=threading.RLock()
        self.config=MapThemeRequest.model_validate_json(self.path.read_text(encoding='utf-8')) if self.path.exists() else MapThemeRequest()
    def save(self,config):
        with self.lock:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp')
            temporary.write_text(config.model_dump_json(indent=2),encoding='utf-8')
            temporary.replace(self.path)
            self.config=config
    def public(self,now=None):
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:raise ValueError('Theme calculations require an aware datetime')
        local=now.astimezone(ZoneInfo(TIMEZONE))
        rise,setting=solar_events(local.date())
        daylight=rise<=local<setting
        next_change=rise if local<rise else setting if local<setting else solar_events(local.date()+timedelta(days=1))[0]
        with self.lock:mode=self.config.mode;show_info=self.config.show_info
        return {'show_info':show_info,'mode':mode,'effective':('day' if daylight else 'night') if mode=='auto' else mode,
                'sunrise':rise.isoformat(),'sunset':setting.isoformat(),
                'next_change_at':next_change.isoformat() if mode=='auto' else None,
                'timezone':TIMEZONE,'latitude':LATITUDE,'longitude':LONGITUDE}
