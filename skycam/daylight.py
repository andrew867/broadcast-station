"""Local calculated solar information, independent of weather/network availability."""
from datetime import datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo
from astral import Observer, moon
from astral.sun import sun, elevation, azimuth
from .map_theme import LATITUDE, LONGITUDE, TIMEZONE

OBSERVER = Observer(LATITUDE, LONGITUDE)
TZ = ZoneInfo(TIMEZONE)

@lru_cache(maxsize=8)
def events(day):
    return sun(OBSERVER, date=day, dawn_dusk_depression=6, tzinfo=TZ)

@lru_cache(maxsize=8)
def curve(day):
    e = events(day)
    start, end = e['dawn'].timestamp(), e['dusk'].timestamp()
    return [{'at': start + (end-start)*i/96,
             'elevation': elevation(OBSERVER, datetime.fromtimestamp(start+(end-start)*i/96, timezone.utc))}
            for i in range(97)]

@lru_cache(maxsize=8)
def sky_curve(day):
    # Timestamp spacing handles 23/25-hour local days without inventing an hour.
    start=datetime.combine(day,time.min,TZ).timestamp()
    end=datetime.combine(day+timedelta(days=1),time.min,TZ).timestamp()
    points=[]
    for i in range(193):
        at=start+(end-start)*i/192
        instant=datetime.fromtimestamp(at,timezone.utc)
        points.append({'at':at,'sun':elevation(OBSERVER,instant),
                       'moon':moon.elevation(OBSERVER,instant)})
    return points

@lru_cache(maxsize=24)
def lunar_events(day):
    result={}
    for key,fn in [('moonrise',moon.moonrise),('moonset',moon.moonset)]:
        try:
            at=fn(OBSERVER,date=day,tzinfo=TZ)
            result[key]=at.isoformat() if at and at.astimezone(TZ).date()==day else None
        except ValueError:result[key]=None
    return result


def lunar_schedule(now):
    if now.tzinfo is None:raise ValueError('Lunar calculations require a timezone')
    day=now.astimezone(TZ).date();result=dict(lunar_events(day))
    for key in ('moonrise','moonset'):
        result['next_'+key]=None
        for offset in range(8):
            at=lunar_events(day+timedelta(days=offset))[key]
            if at and datetime.fromisoformat(at).timestamp()>now.timestamp():
                result['next_'+key]=at;break
    return result


def lunar_display(data,key):
    """Today's event, or the next dated event when none occurs today."""
    at=data.get(key) or data.get('next_'+key)
    if not at:return {'time':'Unavailable','date':'NO EVENT IN NEXT 7 DAYS','next':True}
    instant=datetime.fromisoformat(at).astimezone(TZ)
    today=datetime.fromisoformat(data['date']).date()
    offset=(instant.date()-today).days
    day_label='TODAY' if offset==0 else 'TOMORROW' if offset==1 else instant.strftime('%a').upper()
    return {'time':instant.strftime('%I:%M %p').lstrip('0'),
            'date':day_label+' / '+instant.strftime('%b %d %Z').upper(),'next':not bool(data.get(key))}

def duration(e):
    # UTC seconds avoid wall-clock arithmetic at daylight-saving changes.
    return e['sunset'].timestamp() - e['sunrise'].timestamp()

def public(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('Solar calculations require an aware datetime')
    local = now.astimezone(TZ)
    e = events(local.date())
    phase = ('Night' if local < e['dawn'] or local >= e['dusk'] else
             'Morning twilight' if local < e['sunrise'] else
             'Daylight' if local < e['sunset'] else 'Evening twilight')
    candidates = [(key, value) for key, value in e.items() if value > local]
    if not candidates: candidates = [('dawn', events(local.date()+timedelta(days=1))['dawn'])]
    next_name, next_at = min(candidates, key=lambda row: row[1].timestamp())
    return {'date': local.date().isoformat(), 'timezone': TIMEZONE,
            'latitude': LATITUDE, 'longitude': LONGITUDE, 'calculated_at': local.isoformat(),
            'events': {key: value.isoformat() for key, value in e.items()},
            'daylight_seconds': duration(e),
            'change_seconds': duration(e)-duration(events(local.date()-timedelta(days=1))),
            'phase': phase, 'next_event': next_name, 'next_at': next_at.isoformat(),
            'solar_elevation': elevation(OBSERVER, now), 'curve': curve(local.date()),
            'solar_azimuth':azimuth(OBSERVER,now),
            'moon_elevation':moon.elevation(OBSERVER,now),
            'moon_azimuth':moon.azimuth(OBSERVER,now), 'sky_curve':sky_curve(local.date()),
            **lunar_schedule(now),
            'source': 'Sun and Moon calculated with Astral; unobstructed horizon, civil twilight at 6 degrees below horizon'}
