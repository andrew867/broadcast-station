"""Native weather board with large type; refresh at most twice a minute."""
import time,math
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw
from .graphics import font,fit
from .map_renderer import MapRenderer
from .map_theme import TIMEZONE

def local_time(value):
    if value is None:return 'not reported'
    if isinstance(value,str):dt=datetime.fromisoformat(value)
    else:dt=datetime.fromtimestamp(value,ZoneInfo(TIMEZONE))
    return dt.astimezone(ZoneInfo(TIMEZONE)).strftime('%a %I:%M %p %Z').replace(' 0',' ')
def number(value,suffix='',digits=0):
    return 'Not reported' if value is None else (f'{value:.{digits}f}'+suffix)
def lines(draw,text,x,y,width,size=56,limit=3,fill='#f4f0e7'):
    f=font(size,False);rows=[];line=''
    for word in str(text).split():
        next_line=(line+' '+word).strip()
        if draw.textlength(next_line,font=f)>width and line:rows.append(line);line=word
        else:line=next_line
    if line:rows.append(line)
    if len(rows)>limit:
        rows=rows[:limit];last=rows[-1]
        while draw.textlength(last+'…',font=f)>width:last=last[:-1]
        rows[-1]=last+'…'
    for row in rows:draw.text((x,y),row,font=f,fill=fill);y+=round(size*1.35)
    return y

def condition_kind(text):
    value=str(text).lower()
    if 'thunder' in value:return 'thunder'
    if any(word in value for word in ('freezing rain','ice pellet')) or (any(word in value for word in ('rain','shower')) and any(word in value for word in ('snow','flurr'))):return 'mixed'
    if any(word in value for word in ('snow','flurr')):return 'snow'
    if any(word in value for word in ('rain','shower','drizzle')):return 'rain'
    if any(word in value for word in ('fog','mist','haze','smoke')):return 'fog'
    if any(word in value for word in ('partly','mix of sun','few cloud')):return 'partly'
    if any(word in value for word in ('cloud','overcast')):return 'cloud'
    if any(word in value for word in ('sun','clear')):return 'clear'
    return 'unknown'


def weather_icon(d,text,x,y,size=150,night=False):
    """Small vector symbols; unknown reports get no invented weather condition."""
    kind=condition_kind(text);scale=size/100
    box=lambda a,b,c,e:(x+a*scale,y+b*scale,x+c*scale,y+e*scale)
    line=lambda points,color,width=3:d.line([(x+a*scale,y+b*scale) for a,b in points],fill=color,width=max(1,round(width*scale)))
    if kind=='unknown':
        d.text((x+30*scale,y+12*scale),'?',font=font(round(70*scale)),fill='#b4c6d0');return
    if kind in ('clear','partly'):
        if night:
            d.ellipse(box(16,10,70,64),fill='#dfebf0');d.ellipse(box(35,2,80,47),fill='#203643')
        else:
            d.ellipse(box(26,20,66,60),fill='#ffbe62')
            for i in range(8):
                a=i*math.pi/4;line([(46+26*math.cos(a),40+26*math.sin(a)),(46+35*math.cos(a),40+35*math.sin(a))],'#ffbe62',4)
    if kind not in ('clear','fog'):
        for bounds in [(12,38,62,76),(35,23,78,76),(57,40,93,76)]:d.ellipse(box(*bounds),fill='#dbe6eb')
        d.rounded_rectangle(box(20,52,85,76),radius=8*scale,fill='#dbe6eb')
    if kind in ('rain','mixed'):
        for a in (29,51,73):line([(a,82),(a-5,95)],'#6fc9ec',4)
    if kind in ('snow','mixed'):
        for a in (32,70):
            for angle in (0,math.pi/3,2*math.pi/3):
                line([(a-6*math.cos(angle),87-6*math.sin(angle)),(a+6*math.cos(angle),87+6*math.sin(angle))],'#dbe6eb',2)
    if kind=='thunder':d.polygon([(x+a*scale,y+b*scale) for a,b in [(52,69),(39,87),(52,85),(45,100),(66,77),(54,79)]],fill='#ffbe62')
    if kind=='fog':
        for row in range(4):line([(12+row%2*12,28+row*16),(88-row%2*12,28+row*16)],'#b4c6d0',5)


class WeatherRenderer(MapRenderer):
    def __init__(self,data,weather):
        super().__init__(data,lambda:{'healthy':True,'weather':weather.public()},'weather',17)
        self.weather=weather
    def basemap(self):
        self.base=Image.new('RGBA',(3840,2160),'#101c25');self.built_at=time.time()
    def tick(self):
        with self.lock:
            if time.time()-self.status.get('updated_at',0)<30:return
            return self._tick()
    def ensure(self):self.tick()
    def draw(self,data):
        w=data['weather'];im=self.base.copy();d=ImageDraw.Draw(im);paper='#f4f0e7';muted='#b4c6d0';accent='#ff9a62'
        d.text((192,300),"ST. JOHN'S WEATHER",font=font(108),fill=paper)
        subtitle='OBSERVED '+local_time(w.get('observed_at')).upper()
        if not w['current_available']:subtitle='CURRENT OBSERVATION UNAVAILABLE'
        elif w['cached']:subtitle+='  |  CACHED UPDATE'
        d.text((196,433),subtitle,font=font(38,False),fill=accent)
        d.rounded_rectangle((192,530,1432,1220),radius=22,fill='#203643')
        d.text((240,540),number(w.get('temperature_c'),'°',1) if w.get('temperature_c') is not None else '--°',font=font(260),fill=paper)
        d.text((245,850),'CELSIUS',font=font(34),fill=muted)
        condition=w.get('condition') or 'Observation unavailable'
        weather_icon(d,condition,1160,590,190)
        lines(d,condition,245,920,1110,70,2)
        lines(d,w.get('station') or 'Unavailable',245,1134,1110,34,1,muted)
        metrics=[('WIND',w.get('wind_kmh'),(w.get('wind_direction')+' ' if w.get('wind_direction') else '')+number(w.get('wind_kmh'),' km/h'),
                  'Gusts '+number(w['gust_kmh'],' km/h') if w.get('gust_kmh') else ''),
                 ('HUMIDITY',w.get('humidity_pct'),number(w.get('humidity_pct'),'%'),''),
                 ('PRESSURE',w.get('pressure_kpa'),number(w.get('pressure_kpa'),' kPa',1),''),
                 ('VISIBILITY',w.get('visibility_km'),number(w.get('visibility_km'),' km',1),'')]
        for i,(label,value,display,note) in enumerate(metrics):
            x=1492+(i%2)*1108;y=530+(i//2)*360
            d.rounded_rectangle((x,y,x+1048,y+330),radius=20,fill='#182b36')
            d.text((x+36,y+24),label,font=font(42),fill=accent if value is not None else muted)
            d.text((x+36,y+92),display if value is not None else 'Unavailable',font=fit(d,display if value is not None else 'Unavailable',88 if value is not None else 36,976, value is not None),fill=paper if value is not None else muted)
            if value is not None and note:d.text((x+36,y+240),note,font=font(34,False),fill=muted)
        forecasts=w.get('forecasts',[])
        d.text((196,1260),'THE OUTLOOK',font=font(48),fill=accent)
        issued='FORECAST ISSUED '+local_time(w.get('forecast_at')).upper() if forecasts else 'FORECAST TEMPORARILY UNAVAILABLE'
        d.text((850,1271),issued,font=font(34,False),fill=muted)
        for i in range(3):
            x=192+i*1168;d.rounded_rectangle((x,1360,x+1120,1766),radius=18,fill='#203643')
            if i>=len(forecasts):
                d.text((x+36,1490),'Forecast unavailable',font=font(44),fill=muted);continue
            f=forecasts[i];period=str(f['period']).upper()
            d.text((x+36,1380),period,font=fit(d,period,52,690),fill=paper)
            weather_icon(d,f['summary'],x+900,1390,150,'tonight' in period.lower() or 'night' in period.lower())
            temp=f['temperatures'][0] if f['temperatures'] else None
            if temp:
                label=(str(temp['kind'] or '')+' '+number(temp['value'],'°')).upper()
                d.text((x+36,1460),label,font=fit(d,label,92,800),fill=accent)
            lines(d,f['summary'],x+36,1590,1048,52,2)
        solar='SUNRISE '+local_time(w['sunrise']).split(' ',1)[1]+'  ·  SUNSET '+local_time(w['sunset']).split(' ',1)[1]
        d.text((196,1805),solar,font=font(34,False),fill=muted)
        credit='WEATHER: ENVIRONMENT AND CLIMATE CHANGE CANADA';f=font(32,False)
        d.text((3648-d.textlength(credit,font=f),1805),credit,font=f,fill=muted)
        return im,0
