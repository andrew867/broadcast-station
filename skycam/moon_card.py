from .station_config import CONFIG
"""Approximate daily lunar phase and local rise/set, calculated with Astral."""
import math
from datetime import datetime, timezone
from astral import moon
from PIL import Image, ImageDraw
from .daylight import OBSERVER,TZ,lunar_schedule,lunar_display
from .graphics import font,PAPER

NAMES=('New moon','Waxing crescent','First quarter','Waxing gibbous',
       'Full moon','Waning gibbous','Last quarter','Waning crescent')

def public(now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Lunar calculations require a timezone')
    day=now.astimezone(TZ).date();phase=float(moon.phase(day));angle=phase/28*2*math.pi
    return {'date':day.isoformat(),'phase':phase,'name':NAMES[int((phase+1.75)//3.5)%8],
            'illumination':(1-math.cos(angle))/2,**lunar_schedule(now),
            'source':'Astral, calculated daily approximation','timezone':str(TZ)}

def image(data):
    from .community_cards import heading,MUTED,clock
    im,d=heading('TONIGHT\'S SKY',CONFIG.location.name.upper()+' / '+data['date']+'')
    cx,cy,r=1060,1110,370;phase=data['phase']/28*2*math.pi
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill='#233b4c',outline='#547184',width=4)
    # Orthographic illuminated hemisphere. The right side waxes; orientation
    # is schematic, not the Moon's actual tilt above the observer's horizon.
    for y in range(-r,r+1):
        limb=math.sqrt(max(0,r*r-y*y));terminator=math.cos(phase)*limb
        left,right=(terminator,limb) if phase<=math.pi else (-limb,-terminator)
        if right>left:d.line((cx+left,cy+y,cx+right,cy+y),fill='#eee9d4',width=1)
    d.text((600,1580),'MOON PHASE ILLUSTRATION',font=font(36),fill=MUTED)
    d.text((1770,675),data['name'].upper(),font=font(100),fill=PAPER)
    d.text((1770,830),f"{round(data['illumination']*100)}% ILLUMINATED",font=font(55),fill='#ffb578')
    for y,key,label in ((1050,'moonrise','MOONRISE'),(1370,'moonset','MOONSET')):
        event=lunar_display(data,key)
        d.text((1770,y),('NEXT ' if event['next'] else '')+label,font=font(48),fill=MUTED)
        d.text((1770,y+65),event['time'],font=font(116),fill=PAPER)
        d.text((1770,y+205),event['date'],font=font(43),fill='#9fdcff')
    d.text((192,1865),'ASTRAL / APPROXIMATE LOCAL TIMES',font=font(32,False),fill=MUTED)
    return im
