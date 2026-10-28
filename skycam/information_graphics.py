"""Composite information screens built from timestamped station providers."""
from datetime import datetime,timezone
from . import daylight
from .graphics import font,fit,PAPER,ORANGE

MUTED='#b4c9d5'
PANEL='#203643'
GOOD='#9fe0bd'
WARN='#ffb578'


def _heading(title,subtitle):
    from .community_cards import heading
    return heading(title,subtitle)


def local_time(value,form='%I:%M %p'):
    try:
        stamp=float(value) if isinstance(value,(int,float)) else datetime.fromisoformat(value).timestamp()
        return datetime.fromtimestamp(stamp,daylight.TZ).strftime(form).lstrip('0')
    except (ValueError,TypeError,OSError):return 'Unavailable'


def unavailable(d,message):
    d.text((240,850),message.upper(),font=font(110),fill=PAPER)


def weather_timeline_image(data):
    im,d=_heading('WEATHER TIMELINE',"ST. JOHN'S / OFFICIAL FORECAST")
    if not data.get('forecast_available'):
        unavailable(d,'Official forecast unavailable');return im
    current=f"{data.get('temperature_c'):.0f}°C" if data.get('temperature_c') is not None else 'N/A'
    d.rounded_rectangle((192,620,1000,1760),radius=28,fill='#18303e')
    d.text((250,680),'NOW',font=font(58),fill=ORANGE)
    d.text((250,790),current,font=font(190),fill=PAPER)
    d.text((250,1030),str(data.get('condition') or 'Not reported').upper(),font=fit(d,str(data.get('condition') or ''),60,690),fill=PAPER)
    wind=' '.join(filter(None,[str(data.get('wind_direction') or ''),f"{data.get('wind_kmh'):.0f} km/h" if data.get('wind_kmh') is not None else '']))
    d.text((250,1205),'WIND',font=font(38),fill=MUTED);d.text((250,1260),wind or 'Unavailable',font=fit(d,wind or 'Unavailable',54,690),fill=PAPER)
    d.text((250,1425),'VISIBILITY',font=font(38),fill=MUTED)
    vis=f"{data.get('visibility_km'):.0f} km" if data.get('visibility_km') is not None else 'Unavailable'
    d.text((250,1480),vis,font=font(60),fill=PAPER)
    forecasts=data.get('forecasts',[])[:3]
    for i,row in enumerate(forecasts):
        x=1080+i*850
        d.rounded_rectangle((x,620,x+780,1760),radius=28,fill=PANEL)
        period=str(row.get('period') or 'Forecast').upper()
        d.text((x+45,680),period,font=fit(d,period,55,690),fill=ORANGE)
        temps=row.get('temperatures') or []
        temp=' / '.join(f"{t.get('value'):.0f}°" for t in temps if t.get('value') is not None) or 'Temperature unavailable'
        d.text((x+45,790),temp,font=fit(d,temp,92,690),fill=PAPER)
        summary=str(row.get('summary') or 'Details unavailable')
        from .alert_graphics import wrap
        for j,line in enumerate(wrap(summary,52,680)[:7]):d.text((x+45,1000+j*88),line,font=font(54,False),fill=PAPER)
    checked=data.get('fetched_at')
    d.text((192,1845),'UPDATED '+local_time(checked,'%b %d, %I:%M %p %Z').upper()+' / ENVIRONMENT AND CLIMATE CHANGE CANADA',font=font(35,False),fill=MUTED)
    return im


def travel_image(data):
    im,d=_heading('NL TRAVEL NOW','ROADS / FERRIES / ADVISORIES / 511 NEWFOUNDLAND AND LABRADOR')
    if not data.get('available'):
        unavailable(d,'Travel data unavailable')
        d.text((240,1020),'A 511NL DEVELOPER KEY IS REQUIRED',font=font(48,False),fill=MUTED);return im
    rows=[]
    for label,key in [('ROAD','events'),('ROAD','roads'),('FERRY','ferries'),('WIND','winds'),('ADVISORY','advisories')]:
        for row in data.get(key,[]):rows.append((label,row))
    if not rows:
        d.text((240,800),'NO EXCEPTIONAL TRAVEL ITEMS REPORTED',font=font(90),fill=GOOD)
        d.text((240,950),'Check 511nl.ca before travelling. Conditions can change quickly.',font=font(48,False),fill=MUTED)
    for i,(label,row) in enumerate(rows[:6]):
        y=625+i*190;d.rounded_rectangle((192,y,3648,y+160),radius=18,fill=PANEL)
        d.text((235,y+30),label,font=font(42),fill=ORANGE)
        title=row.get('road') or row.get('service') or row.get('message') or row.get('location') or 'Travel update'
        detail=row.get('description') or row.get('condition') or row.get('status') or row.get('advisory') or row.get('notes') or ''
        d.text((570,y+22),str(title).upper(),font=fit(d,str(title),52,2920),fill=PAPER)
        d.text((570,y+88),str(detail),font=fit(d,str(detail),36,2920,False),fill=MUTED)
    d.text((192,1845),'UPDATED '+local_time(data.get('checked_at'),'%b %d, %I:%M %p %Z').upper()+' / 511NL.CA',font=font(35,False),fill=MUTED)
    return im


def harbour_image(data):
    im,d=_heading('HARBOUR WATCH',"ST. JOHN'S / VESSELS / TIDES / MARINE")
    ais=data.get('ais') or {};tides=data.get('tides') or {};marine=data.get('marine') or {}
    cards=[('FRESH VESSEL POSITIONS',str((ais.get('counts') or {}).get('fresh',0))),
           ('MOVING VESSELS',str((ais.get('counts') or {}).get('moving_fresh',0))),
           ('OLDER POSITIONS',str((ais.get('counts') or {}).get('older',0)))]
    for i,(label,value) in enumerate(cards):
        x=192+i*780;d.rounded_rectangle((x,620,x+720,930),radius=22,fill=PANEL)
        d.text((x+38,665),label,font=fit(d,label,40,644),fill=MUTED);d.text((x+38,745),value,font=font(116),fill=PAPER)
    x=2570;d.rounded_rectangle((x,620,3648,930),radius=22,fill='#18303e')
    d.text((x+40,665),'NEXT TIDE EVENTS',font=font(42),fill=ORANGE)
    for j,event in enumerate((tides.get('events') or [])[:2]):
        kind=str(event.get('kind') or event.get('event') or event.get('type') or 'Tide').upper();height=event.get('value') if event.get('value') is not None else event.get('height_m')
        label=kind+'  '+local_time(event.get('at') or event.get('time'))+(f'  {height:.1f} m' if isinstance(height,(int,float)) else '')
        d.text((x+40,740+j*78),label,font=fit(d,label,47,995),fill=PAPER)
    groups=marine.get('groups') or []
    d.text((192,1040),'COASTAL FORECAST',font=font(54),fill=ORANGE)
    if groups:
        group=groups[0];d.text((192,1120),str(group.get('name') or 'East coast').upper(),font=font(72),fill=PAPER)
        fields=group.get('fields') or {}
        lines=[fields.get('wind'),fields.get('weatherVisibility')]
        from .alert_graphics import wrap
        y=1230
        for text in filter(None,lines):
            for line in wrap(str(text),72,3300)[:3]:d.text((192,y),line,font=font(58,False),fill=PAPER);y+=86
    else:d.text((192,1140),'Marine forecast unavailable',font=font(58,False),fill=MUTED)
    d.text((192,1845),'AIS POSITIONS ARE INCOMPLETE AND NOT FOR NAVIGATION / OFFICIAL TIDES AND ECCC MARINE DATA',font=font(33,False),fill=MUTED)
    return im


def sky_image(data):
    im,d=_heading("TONIGHT'S SKY",'SUNSET / MOON / VIEWING CONDITIONS / GEOMAGNETIC FORECAST')
    solar=data.get('daylight') or {};weather=data.get('weather') or {};space=data.get('space') or {}
    events=solar.get('events') or {};moonrise=daylight.lunar_display(solar,'moonrise') if solar else {'time':'Unavailable','date':'','next':False}
    moonset=daylight.lunar_display(solar,'moonset') if solar else {'time':'Unavailable','date':'','next':False}
    cards=[('SUNSET',local_time(events.get('sunset'))),('MOONRISE',moonrise['time']),('MOONSET',moonset['time'])]
    for i,(label,value) in enumerate(cards):
        x=192+i*790;d.rounded_rectangle((x,620,x+730,940),radius=22,fill=PANEL)
        d.text((x+42,665),label,font=font(48),fill=ORANGE);d.text((x+42,765),value,font=fit(d,value,92,646),fill=PAPER)
    x=2580;d.rounded_rectangle((x,620,3648,940),radius=22,fill='#18303e')
    d.text((x+42,665),'MOON PHASE',font=font(48),fill=ORANGE)
    moon=data.get('moon') or {};phase=str(moon.get('name') or moon.get('phase_name') or 'Unavailable')
    d.text((x+42,765),phase.upper(),font=fit(d,phase,74,980),fill=PAPER)
    d.text((192,1050),'VIEWING CONDITIONS',font=font(54),fill=ORANGE)
    condition=str(weather.get('condition') or 'Observation unavailable')
    forecasts=weather.get('forecasts') or [];forecast=str(forecasts[0].get('summary')) if forecasts else 'Forecast unavailable'
    d.text((192,1130),condition.upper(),font=fit(d,condition,82,2200),fill=PAPER)
    d.text((192,1240),forecast,font=fit(d,forecast,54,2200,False),fill=MUTED)
    d.text((2580,1050),'GEOMAGNETIC ACTIVITY',font=font(50),fill=ORANGE)
    if space.get('available'):
        current=(space.get('current') or {}).get('sub_auroral','Unavailable')
        forecast=(space.get('forecast_24h') or {}).get('sub_auroral','Unavailable')
        d.text((2580,1130),str(current).upper(),font=fit(d,str(current),72,1068),fill=PAPER)
        d.text((2580,1240),'24 HOUR: '+str(forecast).upper(),font=fit(d,'24 HOUR: '+str(forecast),44,1068),fill=MUTED)
    else:
        d.text((2580,1130),'UNAVAILABLE',font=font(72),fill=MUTED)
    d.text((192,1845),'ASTRONOMICAL TIMES CALCULATED FOR '+str(data.get('location','LOCAL AREA')).upper()+' / SPACE WEATHER: NATURAL RESOURCES CANADA',font=font(33,False),fill=MUTED)
    return im


def briefing_image(data,kind):
    morning=kind=='morning';title='MORNING BRIEFING' if morning else 'EVENING BRIEFING'
    subtitle=('START THE DAY' if morning else 'TONIGHT AND TOMORROW')+' / '+str(data.get('location','LOCAL AREA')).upper()
    im,d=_heading(title,subtitle)
    weather=data.get('weather') or {};travel=data.get('travel') or {};outages=data.get('outages') or {}
    temp=f"{weather.get('temperature_c'):.0f}°C" if weather.get('temperature_c') is not None else 'N/A'
    summary=str(weather.get('condition') or 'Observation unavailable')
    forecasts=weather.get('forecasts') or []
    forecast=str(forecasts[0].get('summary')) if forecasts else 'Forecast unavailable'
    sections=[('RIGHT NOW',temp+'  '+summary),('FORECAST',forecast),
              ('TRAVEL',travel.get('summary') or 'Travel data unavailable'),
              ('POWER',f"{len(outages.get('active') or [])} current outage"+('s' if len(outages.get('active') or [])!=1 else '') if outages.get('fresh') else 'Outage data unavailable')]
    for i,(label,value) in enumerate(sections):
        y=620+i*285;d.rounded_rectangle((192,y,3648,y+245),radius=22,fill=PANEL if i%2 else '#18303e')
        d.text((245,y+38),label,font=font(48),fill=ORANGE)
        d.text((920,y+47),str(value),font=fit(d,str(value),68,2660,False),fill=PAPER)
    d.text((192,1845),'OFFICIAL SOURCES / CHECK SOURCE PAGES FOR COMPLETE DETAILS',font=font(35,False),fill=MUTED)
    return im


def calendar_image(items,now):
    im,d=_heading('COMMUNITY CALENDAR','APPROVED LOCAL EVENTS AND NOTICES')
    rows=[]
    for item in items:
        if not item.get('approved'):continue
        try:
            starts=datetime.fromisoformat(item['starts_at']).timestamp() if item.get('starts_at') else now.timestamp()
            ends=datetime.fromisoformat(item['ends_at']).timestamp() if item.get('ends_at') else starts+14*86400
        except (TypeError,ValueError):continue
        if ends>=now.timestamp() and starts<=now.timestamp()+21*86400:rows.append((starts,item))
    rows.sort(key=lambda row:(row[0],row[1].get('title','')))
    if not rows:
        unavailable(d,'No approved upcoming events');return im
    for i,(starts,item) in enumerate(rows[:6]):
        y=625+i*190;dt=datetime.fromtimestamp(starts,daylight.TZ)
        d.rounded_rectangle((192,y,3648,y+160),radius=18,fill=PANEL)
        d.text((235,y+22),dt.strftime('%b').upper(),font=font(38),fill=ORANGE)
        d.text((235,y+66),str(dt.day),font=font(70),fill=PAPER)
        title=str(item.get('title') or 'Community event')
        location=str(item.get('location') or '')
        d.text((500,y+25),title.upper(),font=fit(d,title,52,3050),fill=PAPER)
        detail=' / '.join(filter(None,[dt.strftime('%I:%M %p').lstrip('0') if item.get('starts_at') else '',location,item.get('credit','')]))
        d.text((500,y+95),detail,font=fit(d,detail,34,3050,False),fill=MUTED)
    return im
