"""Native broadcast cards for dated PUB history and digitised daily curves."""
from datetime import date,datetime
from .graphics import font,fit,PAPER
from .community_cards import heading,MUTED

def label(value):return date.fromisoformat(value).strftime('%b %d, %Y').upper()
def chart(d,points,box,color,day_axis=False,max_value=None,axes=True):
    left,top,right,bottom=box
    if not points:return
    lo=0;hi=max_value or max(200,((max(v for x,v in points)+199)//200)*200)
    for frac in ((0,.25,.5,.75,1) if axes else ()):
        y=bottom-frac*(bottom-top);d.line((left,y,right,y),fill='#3b5362',width=2)
        d.text((left-110,y-24),f'{hi*frac:,.0f}',font=font(34),fill=MUTED)
    start,end=points[0][0],points[-1][0];span=max(1,end-start);prev=None
    for x,v in points:
        xx=left+(x-start)/span*(right-left);yy=bottom-v/hi*(bottom-top)
        if prev and (not day_axis or x-prev[2]<=1):d.line((prev[0],prev[1],xx,yy),fill=color,width=9)
        if day_axis:d.ellipse((xx-8,yy-8,xx+8,yy+8),fill=color)
        prev=(xx,yy,x)

def image(data,scene):
    r=data.get('latest');title='ISLAND ELECTRICITY HISTORY' if scene=='power-history' else 'ISLAND SUPPLY & DEMAND'
    im,d=heading(title,('PUB REPORT FILED '+label(r.get('filed_date',r['report_date']))) if r else 'NEWFOUNDLAND & LABRADOR HYDRO / PUB REPORTS')
    if not r:
        d.text((240,900),'REPORT HISTORY NOT AVAILABLE',font=font(110),fill=PAPER);return im
    if scene=='power-history':
        cards=[('LATEST DAILY PEAK',f"{r['peak_mw']:,}",'MW',label(r['actual_date'])+' / '+r['peak_time']),('EXPORTS AT THAT PEAK',f"{r['exports_at_peak_mw']:,}",'MW',label(r['actual_date'])),('DAILY LIL NET IMPORTS',f"{r['lil_energy_mwh']:,}",'MWh',label(r['actual_date']))]
        for i,(name,value,unit,detail) in enumerate(cards):
            x=192+i*1168;d.rounded_rectangle((x,620,x+1120,990),radius=18,fill='#203643')
            d.text((x+35,644),name,font=font(48),fill='#6dd6df');d.text((x+35,710),value,font=font(148),fill=PAPER);d.text((x+870,805),unit,font=font(46),fill=PAPER);d.text((x+35,920),detail,font=font(35),fill=MUTED)
        rows=data.get('trend',[])[-90:];d.text((192,1040),'DAILY PEAK ISLAND DEMAND / MW',font=font(48),fill=PAPER)
        if rows:
            points=[(date.fromisoformat(p['day']).toordinal(),p['mw']) for p in rows];chart(d,points,(330,1170,3510,1710),'#6dd6df',True)
            for f in (0,.25,.5,.75,1):
                x=330+f*(3510-330);text=date.fromordinal(round(points[0][0]+f*(points[-1][0]-points[0][0]))).strftime('%b %d').upper();d.text((min(3320,max(192,x-80)),1740),text,font=font(36),fill=MUTED)
        d.text((192,1850),'PRINTED DAILY VALUES / GAPS PRESERVED / SOURCE: NL HYDRO VIA PUB.NF.CA',font=font(35),fill=MUTED)
    else:
        d.text((192,625),'ACTUAL DAY / '+label(r['actual_date']),font=font(55),fill=PAPER)
        colors={'island-supply':'#f4bd75','island-demand':'#6dd6df','supply-including-export':'#a4d484','demand-including-export':'#b2acff'}
        c=r.get('chart');box=(310,880,2240,1620)
        if c:
            high=max(v['mw'] for points in c['series'].values() for v in points);high=max(200,((high+199)//200)*200)
            for i,(key,points) in enumerate(c['series'].items()):chart(d,[(p['minute'],p['mw']) for p in points],box,colors[key],max_value=high,axes=(i==0))
            for h in (0,6,12,18,24):d.text((max(192,310+h/24*1930-65),1650),f'{h:02d}:00',font=font(34),fill=MUTED)
        else:d.text((320,1120),'CHART COULD NOT BE VERIFIED',font=fit(d,'CHART COULD NOT BE VERIFIED',72,1800),fill=MUTED)
        labels=[('island-demand','ISLAND DEMAND'),('island-supply','ISLAND SUPPLY'),('demand-including-export','DEMAND WITH ML EXPORTS'),('supply-including-export','SUPPLY WITH LIL FOR ML EXPORTS')]
        for i,(key,text) in enumerate(labels):
            x=192+(i%2)*1120;y=720+(i//2)*60;d.text((x,y),text,font=fit(d,text,35,1090),fill=colors[key])
        d.rounded_rectangle((2390,620,3648,1770),radius=18,fill='#203643')
        d.text((2430,650),'SEVEN-DAY FORECAST / MW',font=font(50),fill=PAPER)
        d.text((2430,720),'FILED '+label(r.get('filed_date',r['report_date'])),font=font(36),fill=MUTED)
        d.text((3000,790),'FORECAST',font=font(32),fill='#f4bd75');d.text((3350,790),'ADJUSTED',font=font(32),fill=MUTED)
        for i,row in enumerate(r['forecast']):
            y=855+i*98;d.text((2430,y),date.fromisoformat(row['day']).strftime('%a %b %d').upper(),font=font(42),fill=PAPER)
            d.text((3000,y),f"{row['forecast_mw']:,}",font=font(52),fill='#f4bd75');d.text((3350,y),f"{row['adjusted_mw']:,}",font=font(52),fill=MUTED)
        d.text((2430,1590),'Adjusted for interruptible load and',font=font(31,False),fill=MUTED);d.text((2430,1640),'voltage reduction where applicable.',font=font(31,False),fill=MUTED)
        d.text((192,1820),'CURVES APPROXIMATED FROM THE PUBLISHED GRAPH / NEWFOUNDLAND LOCAL TIME',font=font(35),fill=MUTED)
        d.text((192,1880),'DATED REPORT, NOT LIVE READINGS / SOURCE: NL HYDRO VIA PUB.NF.CA',font=font(35),fill=MUTED)
    return im
