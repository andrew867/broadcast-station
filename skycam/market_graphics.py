"""Native market cards with explicit comparison windows and bounded trends."""
import math
from datetime import datetime
from .graphics import font,fit,PAPER
from .daylight import TZ

UP='#66dfac';DOWN='#ff8a92';NEUTRAL='#b4c9d5'


def movement(value,precision=4):
    if value is None or not math.isfinite(value):return 'unknown',NEUTRAL
    rounded=round(value,precision)
    return ('up',UP) if rounded>0 else ('down',DOWN) if rounded<0 else ('flat',NEUTRAL)


def arrow(d,x,y,direction,color,size=32):
    if direction in ('up','down'):
        sign=-1 if direction=='up' else 1
        d.polygon([(x,y+sign*size),(x-size,y-sign*size/2),(x+size,y-sign*size/2)],fill=color)
    else:d.line((x-size,y,x+size,y),fill=color,width=7)


def trend_points(history,box):
    """Use real observation spacing and label the non-zero-based price scale."""
    rows=[p for p in history if isinstance(p.get('value'),(int,float)) and math.isfinite(p['value']) and isinstance(p.get('at'),(int,float)) and math.isfinite(p['at'])]
    if len(rows)<2 or rows[-1]['at']<=rows[0]['at']:return [],None,None
    low=min(p['value'] for p in rows);high=max(p['value'] for p in rows)
    span=max(high-low,abs(high)*.00001,1e-6);pad=span*.15
    left,top,right,bottom=box
    points=[(left+(right-left)*(p['at']-rows[0]['at'])/(rows[-1]['at']-rows[0]['at']),
             bottom-(bottom-top)*(p['value']-low+pad)/(span+2*pad)) for p in rows]
    return points,low,high


def image(data):
    if any(r.get('id')=='tsx' for r in data.get('cards',[])):
        return overview_image(data)
    from .community_cards import heading,MUTED
    im,d=heading('MARKET WATCH','01 / 03  /  CURRENCY & ENERGY  /  TIMESTAMPED PRICES')
    for i,row in enumerate(data.get('cards',[])[:3]):
        x=192+i*1176;y=620;w=1104;available=row.get('available',False)
        live=not row.get('daily_reference',True)
        precision=6 if row['id']=='fx' else 3
        delta=row.get('window_change') if live else row.get('change')
        percent=row.get('window_percent') if live else row.get('change_percent')
        direction,color=movement(delta if available else None,precision)
        d.rounded_rectangle((x,y,x+w,1740),radius=22,fill='#19313f',outline='#345260',width=2)
        d.rounded_rectangle((x,y,x+w,y+12),radius=6,fill=color)
        title={'fx':'CANADIAN DOLLAR','wti':'WTI CRUDE','brent':'BRENT CRUDE'}.get(row['id'],row['label'])
        d.text((x+44,y+35),title,font=fit(d,title,76,w-88),fill=PAPER)
        kind=('FX PROVIDER UPDATE' if row['id']=='fx' else 'OANDA OIL CFD') if live else 'DATED DAILY REFERENCE'
        d.text((x+44,y+125),kind,font=font(36),fill='#9fdcff' if live else '#ffb578')
        value=(f"{row['value']:.5f}" if row['id']=='fx' else f"${row['value']:,.3f}" if live else f"${row['value']:,.2f}") if available else 'UNAVAILABLE'
        d.text((x+44,y+190),value,font=fit(d,value,186,w-88),fill=PAPER)
        d.text((x+44,y+390),'USD FOR 1 CAD' if row['id']=='fx' else 'USD / CFD UNIT' if live else 'USD PER BARREL',font=font(42),fill=MUTED)
        if available:arrow(d,x+76,y+488,direction,color)
        if available and delta is not None:
            signed=f'{delta:+.{precision}f}' if direction!='flat' else f'{0:.{precision}f}'
            pct=f' ({percent:+.3f}%)' if percent is not None else ''
            text=signed+pct
        else:text='Unavailable' if available and live else ''
        d.text((x+135,y+444),text,font=fit(d,text,74,w-180),fill=color)
        if live:
            at=row.get('window_start_at')
            basis='SINCE '+datetime.fromtimestamp(at,TZ).strftime('%I:%M:%S %p %Z').lstrip('0') if at else 'Unavailable'
        else:basis='VS '+row['previous_date']+' OBSERVATION' if row.get('previous_date') else 'PREVIOUS OBSERVATION UNAVAILABLE'
        if not available:basis=''
        d.text((x+44,y+540),basis,font=fit(d,basis,35,w-88,False),fill=MUTED)
        history=row.get('history',[]) if available else []
        chart=(x+56,y+650,x+w-56,y+850)
        d.text((x+44,y+605),'RECENT PRICES' if live else 'RECENT DAILY OBSERVATIONS',font=font(34),fill=MUTED)
        for ratio in (0,.5,1):
            line_y=chart[1]+(chart[3]-chart[1])*ratio
            d.line((chart[0],line_y,chart[2],line_y),fill='#35505f',width=2)
        points,low,high=trend_points(history,chart)
        if points:
            d.polygon([*points,(points[-1][0],chart[3]),(points[0][0],chart[3])],fill='#233f46' if direction!='down' else '#3c303e')
            d.line(points,fill=color,width=6)
            px,py=points[-1];d.ellipse((px-8,py-8,px+8,py+8),fill=PAPER)
            digits=5 if row['id']=='fx' else 3 if live else 2
            label=f'LOW {low:.{digits}f}    HIGH {high:.{digits}f}'
        else:
            d.text((x+100,y+718),'Unavailable' if available else '',font=font(48),fill=MUTED)
            label=''
        d.text((x+44,y+875),label,font=fit(d,label,38,w-88),fill=MUTED)
        if live and row.get('observed_at'):
            at=datetime.fromtimestamp(row['observed_at'],TZ)
            stamp=at.strftime('%b %d / %I:%M:%S %p %Z').upper()
            state=('CACHED / ' if row.get('cached') else '')+f"{round(row.get('age_seconds',0))}s SINCE SOURCE UPDATE"
        else:
            stamp=row.get('date') or 'NO DATED OBSERVATION'
            state='CACHED DAILY REFERENCE' if row.get('cached') else 'DAILY REFERENCE / NOT A LIVE QUOTE'
        if not available:stamp=state=''
        d.text((x+44,y+955),stamp,font=fit(d,stamp,43,w-88),fill=PAPER)
        d.text((x+44,y+1020),state,font=fit(d,state,32,w-88,False),fill='#ffb578' if row.get('cached') else MUTED)
        d.text((x+44,y+1070),row['source'],font=font(30,False),fill=MUTED)
    return im


def overview_image(data):
    """Four instruments, with per-source units, comparison and timing semantics."""
    from .community_cards import heading,MUTED
    im,d=heading('MARKET WATCH','01 / 03  /  CANADA, CURRENCY & ENERGY')
    rows={r['id']:r for r in data.get('cards',[])}
    for i,key in enumerate(('tsx','fx','wti','brent')):
        row=rows.get(key,{})
        x=192+(i%2)*1760;y=620+(i//2)*570;w=1696
        available=row.get('available',False);tsx=key=='tsx';daily=row.get('daily_reference',False)
        delta=row.get('change') if tsx or daily else row.get('window_change')
        percent=row.get('change_percent') if tsx or daily else row.get('window_percent')
        direction,color=movement(delta if available else None,5 if key=='fx' else 2)
        d.rounded_rectangle((x,y,x+w,y+530),radius=20,fill='#19313f',outline='#345260',width=2)
        d.rectangle((x+20,y,x+w-20,y+10),fill=color)
        title={'tsx':'S&P/TSX COMPOSITE','fx':'CANADIAN DOLLAR','wti':'WTI CRUDE','brent':'BRENT CRUDE'}[key]
        d.text((x+40,y+25),title,font=fit(d,title,72,w-80),fill=PAPER)
        unit='INDEX POINTS' if tsx else 'USD FOR 1 CAD' if key=='fx' else 'USD PER BARREL / DAILY SPOT' if daily else 'USD / OANDA OIL CFD'
        d.text((x+40,y+110),unit,font=font(32),fill='#9fdcff')
        value=(f"{row['value']:,.2f}" if tsx else f"{row['value']:.5f}" if key=='fx' else f"${row['value']:,.3f}") if available else 'UNAVAILABLE'
        d.text((x+40,y+155),value,font=fit(d,value,145,850),fill=PAPER)
        if available:arrow(d,x+66,y+348,direction,color,25)
        text=(f'{delta:+.5f}' if key=='fx' else f'{delta:+.2f}')+(f' ({percent:+.2f}%)' if percent is not None else '') if available and delta is not None else ''
        d.text((x+115,y+310),text,font=fit(d,text,60,775),fill=color)
        at=row.get('window_start_at')
        basis='VS PREVIOUS CLOSE / TMX' if tsx else ('VS '+row['previous_date']+' / DAILY' if row.get('previous_date') else 'NO PRIOR DAILY OBSERVATION') if daily else ('SINCE '+datetime.fromtimestamp(at,TZ).strftime('%I:%M:%S %p %Z').lstrip('0') if at else 'Unavailable')
        if not available:basis=''
        d.text((x+40,y+390),basis,font=fit(d,basis,32,850,False),fill=MUTED)
        chart=(x+970,y+190,x+w-45,y+340)
        for ratio in (0,.5,1):
            line_y=chart[1]+(chart[3]-chart[1])*ratio
            d.line((chart[0],line_y,chart[2],line_y),fill='#35505f',width=2)
        points,low,high=trend_points(row.get('history',[]) if available else [],chart)
        if points:d.line(points,fill=color,width=6)
        label='DAILY HISTORY' if tsx else 'DAILY OBSERVATIONS' if daily else 'RECENT PRICES'
        if not points:label='Unavailable'
        d.text((x+970,y+365),label,font=fit(d,label,31,w-1015),fill=MUTED)
        detail=('THROUGH '+row['history'][-1]['date']+' / PROVISIONAL') if tsx and points else (f'LOW {low:,.3f} / HIGH {high:,.3f}') if points else ''
        d.text((x+970,y+410),detail,font=fit(d,detail,28,w-1015,False),fill=MUTED)
        if tsx:
            stamp='QUOTE TIME UNAVAILABLE'
            if not available:stamp='QUOTE UNAVAILABLE'
            elif row.get('cached'):stamp='CACHED / '+stamp
        elif daily:stamp=(row.get('date') or 'NO DATE')+' / '+('CACHED ' if row.get('cached') else '')+'DAILY REFERENCE'
        else:stamp=datetime.fromtimestamp(row['observed_at'],TZ).strftime('%b %d %I:%M:%S %p %Z').upper() if available and row.get('observed_at') else 'NO CURRENT SOURCE OBSERVATION'
        if not available:stamp=''
        d.text((x+40,y+466),stamp,font=fit(d,stamp,30,1290,False),fill=MUTED)
        source=row.get('source','')
        d.text((x+w-310,y+465),source,font=fit(d,source,27,275),fill=MUTED)
    return im


def grid_image(data,page):
    from .community_cards import heading,MUTED
    from .live_markets import METALS,STOCKS
    metals=page==1
    keys=METALS if metals else STOCKS
    im,d=heading('PRECIOUS METALS' if metals else 'STOCK WATCH',
                 ('02' if metals else '03')+' / 03  /  '+('GOLD, SILVER, PLATINUM & PALLADIUM' if metals else 'APPLE, MICROSOFT, NVIDIA & ALPHABET'))
    rows={r['id']:r for r in data.get('cards',[])}
    for i,key in enumerate(keys):
        row=rows.get(key,{})
        x=192+(i%2)*1760;y=620+(i//2)*570;w=1696
        available=row.get('available',False);delta=row.get('window_change');percent=row.get('window_percent')
        direction,color=movement(delta if available else None,3)
        d.rounded_rectangle((x,y,x+w,y+530),radius=20,fill='#19313f',outline='#345260',width=2)
        d.rectangle((x+20,y,x+w-20,y+10),fill=color)
        title=row.get('label',key.upper())
        d.text((x+40,y+25),title,font=fit(d,title,72,w-80),fill=PAPER)
        d.text((x+40,y+110),'OANDA METAL CFD / USD' if metals else 'USD PER SHARE',font=font(32),fill='#9fdcff')
        value=f"${row['value']:,.3f}" if available else 'UNAVAILABLE'
        d.text((x+40,y+160),value,font=fit(d,value,145,850),fill=PAPER)
        if available and delta is not None:arrow(d,x+66,y+352,direction,color,25)
        text=(f'{delta:+.3f}'+(f' ({percent:+.3f}%)' if percent is not None else '')) if available and delta is not None else ''
        d.text((x+115,y+310),text,font=fit(d,text,60,775),fill=color)
        at=row.get('window_start_at')
        basis='SINCE '+datetime.fromtimestamp(at,TZ).strftime('%I:%M:%S %p %Z').lstrip('0') if available and at else ''
        if not available:basis=''
        d.text((x+40,y+390),basis,font=fit(d,basis,30,850,False),fill=MUTED)
        chart=(x+970,y+190,x+w-45,y+340)
        for ratio in ((0,.5,1) if len(row.get('history',[]))>1 and available else ()):
            line_y=chart[1]+(chart[3]-chart[1])*ratio
            d.line((chart[0],line_y,chart[2],line_y),fill='#35505f',width=2)
        points,low,high=trend_points(row.get('history',[]) if available else [],chart)
        if points:
            d.line(points,fill=color,width=6)
            px,py=points[-1];d.ellipse((px-7,py-7,px+7,py+7),fill=PAPER)
            label=f'LOW {low:,.3f} / HIGH {high:,.3f}'
        else:label='Unavailable' if available else ''
        d.text((x+970,y+365),label,font=fit(d,label,32,w-1015),fill=MUTED)
        d.text((x+970,y+410),'RECENT PRICES' if points else '',font=font(28),fill=MUTED)
        stamp=(datetime.fromtimestamp(row['observed_at'],TZ).strftime('%b %d %I:%M:%S %p %Z').upper()+f" / {round(row.get('age_seconds',0))}s AGO") if available and row.get('observed_at') else 'NO CURRENT QUOTE'
        if not metals and available and row.get('observed_at'):
            stamp=('LAST QUOTE / ' if row.get('quote_status')=='last_quote' else 'UPDATED / ')+datetime.fromtimestamp(row['observed_at'],TZ).strftime('%b %d %I:%M:%S %p %Z').upper()
        if not available:stamp=''
        d.text((x+40,y+462),stamp,font=fit(d,stamp,31,1200,False),fill=MUTED)
        d.text((x+w-310,y+465),'FINNHUB / OANDA' if metals else 'FINNHUB',font=font(27),fill=MUTED)
    return im
