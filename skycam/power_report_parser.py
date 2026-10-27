"""Strict parser for the PUB one-page Island Supply and Demand report family."""
import io, math, re
from datetime import datetime, timedelta

VERSION='pub-island-2'
DATE=r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}'
SERIES={'island-supply':((.745,.294,.282),'Island System Supply'),
 'island-demand':((0,0,1),'Island System Demand'),
 'supply-including-export':((.2,.4,0),'Island System Supply Plus LIL for ML Exports'),
 'demand-including-export':((.439,.188,.627),'Island System Demand Plus ML Exports')}

def day(value):return datetime.strptime(' '.join(value.split()),'%A, %B %d, %Y').date()
def number(value,ceiling=10000,signed=False):
    text=re.sub(r'[ ,]','',value)
    negative=text.startswith('(') and text.endswith(')')
    if negative:text=text[1:-1]
    if negative and not signed:raise ValueError('Unexpected negative value')
    if not text.isdigit():raise ValueError('Invalid numeric table field')
    n=int(text)
    if not 0<=n<=ceiling:raise ValueError('Table field outside expected range')
    return -n if negative else n

def parse_text(text,expected):
    def one(pattern,area=text):
        hits=re.findall(pattern,area,re.M)
        if len(hits)!=1:raise ValueError('Missing or ambiguous report field: '+pattern[:50])
        return hits[0]
    filed=day(one(r'Status Report Filed\s+('+DATE+')'))
    actual=day(one(r'Actual 24 Hour System Performance For\s+('+DATE+')'))
    outlook_date=datetime.strptime(expected,'%Y-%m-%d').date()
    if actual!=outlook_date-timedelta(days=1) or not 0<=(filed-outlook_date).days<=4:raise ValueError('Report dates disagree with source filename')
    peak,at=one(r'Peak Island System Demand\s*=\s*([\d,]+)\s*MW\s*@\s*(\d{4})')
    datetime.strptime(at,'%H%M');peak=number(peak)
    if text.count('Section 2')!=1 or text.count('Section 3')!=1:raise ValueError('Unrecognised report sections')
    outlook=text.split('Section 2')[1].split('Section 3')[0];last=text.split('Section 3')[1]
    metrics={}
    for key,label in [('supply','Island System Supply'),('generation','NLH Island Generation'),('purchases','NLH Island Power Purchases'),('other-generation','NP and CBPP Owned Generation'),('lil-import','LIL Net Imports to Island'),('seven-day-peak','7-Day Island Peak Demand Forecast')]:
        raw=one(r'^'+re.escape(label)+r':[\d,]*\s+([-()\d ,]+)\s*MW\b',outlook)
        metrics[key]=None if raw.strip()=='-' else number(raw,signed=(key=='lil-import'))
    forecasts=[]
    for date,forecast,adjusted in re.findall('('+DATE+r')\s+([\d,]+)\s+([\d,]+)\s*$',outlook,re.M):
        forecasts.append({'day':day(date).isoformat(),'forecast_mw':number(forecast),'adjusted_mw':number(adjusted)})
    if [f['day'] for f in forecasts]!=[(outlook_date+timedelta(days=i)).isoformat() for i in range(7)]:raise ValueError('Incomplete seven-day forecast')
    if metrics['seven-day-peak']!=max(r['forecast_mw'] for r in forecasts):raise ValueError('Forecast peak cross-check failed')
    if all(v is not None for v in metrics.values()) and abs(metrics['supply']-sum(metrics[k] for k in ('generation','purchases','other-generation','lil-import')))>4:raise ValueError('Supply components cross-check failed')
    peak2=number(one(r'(?<!Forecast )Island Peak Demand\d*\s+\d{1,2}:\d{2}\s+([\d,]+)\s+MW',last))
    if peak!=peak2:raise ValueError('Printed daily peak cross-check failed')
    today=number(one(r'Forecast Island Peak Demand\s+([\d,]+)\s+MW',last))
    if today!=forecasts[0]['forecast_mw']:raise ValueError('Current forecast cross-check failed')
    return {'report_date':expected,'filed_date':filed.isoformat(),'actual_date':actual.isoformat(),'peak_mw':peak,'peak_time':at[:2]+':'+at[2:],
      'exports_at_peak_mw':number(one(r'Exports at Peak\s+([\d,]+)\s+MW',last)),
      'lil_energy_mwh':number(one(r'LIL Net Imports to Island\s+([\d,]+)\s+MWh',last),30000),
      'outlook':metrics,'unreported_fields':[k for k,v in metrics.items() if v is None],'forecast':forecasts,'parser_version':VERSION,'table_method':'printed-table','page':1}

def parse_chart(page,report,text):
    # Only the verified vector template is digitised. Never infer a missing curve.
    curves=[c for c in page.curves if len(c['pts'])==289 and c['x1']-c['x0']>page.width*.5 and c['bottom']<page.height*.4]
    if len(curves)!=4:raise ValueError('Expected four 289-point vector curves')
    left=min(c['x0'] for c in curves);right=max(c['x1'] for c in curves);scale=page.width/612
    grids=[l for l in page.lines if l['x0']<=left and l['x1']>=right and abs(l['top']-l['bottom'])<.01 and 50*scale<l['top']<page.height*.35]
    ys=sorted(set(round(l['top'],2) for l in grids))
    if len(ys)<6:raise ValueError('Chart grid not recognised')
    # Match printed upright axis numbers to horizontal grid lines.
    words=page.filter(lambda o:o['object_type']!='char' or o.get('upright',True)).extract_words()
    ticks=[]
    for w in words:
        if w['text'].isdigit() and left-28*scale<w['x0']<left and w['x1']<left:
            y=min(ys,key=lambda y:abs(y-(w['top']+w['bottom'])/2))
            if abs(y-(w['top']+w['bottom'])/2)<2*scale:ticks.append((y,int(w['text'])))
    ticks=sorted(set(ticks))
    if len(ticks)<6:raise ValueError('Chart axis labels unavailable')
    y1,v1=ticks[0];y2,v2=ticks[-1];slope=(v2-v1)/(y2-y1)
    if slope>=0 or any(abs(v-(v1+(y-y1)*slope))>3 for y,v in ticks):raise ValueError('Nonlinear or ambiguous chart axis')
    rows={}
    for key,(color,label) in SERIES.items():
        if label not in text:raise ValueError('Chart legend changed')
        matches=[c for c in curves if isinstance(c['stroking_color'],(list,tuple)) and len(c['stroking_color'])==3 and max(abs(a-b) for a,b in zip(c['stroking_color'],color))<.015]
        if len(matches)!=1:raise ValueError('Chart series colour ambiguous')
        c=matches[0];pts=c['pts'];step=(right-left)/288
        if any(abs(x-(left+i*step))>step*.12 for i,(x,y) in enumerate(pts)):raise ValueError('Chart time spacing changed')
        values=[round(v1+(y-y1)*slope) for x,y in pts]
        if any(not 0<=v<=10000 for v in values):raise ValueError('Digitised curve outside expected range')
        rows[key]=[{'minute':i*5,'mw':v} for i,v in enumerate(values)]
    peak=max(p['mw'] for p in rows['island-demand'])
    h,m=map(int,report['peak_time'].split(':'));reported=h*60+m
    near=[p['mw'] for p in rows['island-demand'] if abs(p['minute']-reported)<=10]
    if abs(peak-report['peak_mw'])>12 or not near or abs(max(near)-report['peak_mw'])>15:raise ValueError('Chart and printed peak disagree')
    return {'method':'vector-digitised','approximate':True,'nominal_step_minutes':5,'series':rows}

def parse_pdf(raw,expected):
    if len(raw)>4_000_000 or not raw.startswith(b'%PDF-'):raise ValueError('Not a bounded PDF report')
    import pdfplumber
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if len(pdf.pages)!=1:raise ValueError('Unsupported report page count')
        p=pdf.pages[0]
        if not (500<=p.width<=1200 and 700<=p.height<=1600 and abs(p.width/p.height-612/792)<.01):raise ValueError('Unsupported report page size')
        text=p.extract_text() or ''
        if len(text)>50000:raise ValueError('Report text exceeds limit')
        report=parse_text(text,expected)
        try:report['chart']=parse_chart(p,report,text);report['chart_error']=None
        except ValueError as exc:report['chart']=None;report['chart_error']=str(exc)
        return report

if __name__=='__main__':
    import sys,json
    from pathlib import Path
    if sys.platform=='linux':
        import resource,os
        os.nice(10)
        resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(20,20))
    print(json.dumps(parse_pdf(Path(sys.argv[1]).read_bytes(),sys.argv[2])))
