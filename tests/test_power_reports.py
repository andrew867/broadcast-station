import asyncio,json,math
from datetime import datetime,timedelta
from types import SimpleNamespace
import pytest,httpx
from skycam.power_report_parser import parse_text,parse_chart,parse_pdf,SERIES
from skycam.power_reports import PowerReports,report_date,fetch
from skycam.power_report_graphics import image

def report_text():
    start=datetime(2026,10,16)
    rows='\n'.join((start+timedelta(days=i)).strftime('%A, %B %d, %Y')+' 900 850' for i in range(7))
    return '''Newfoundland Labrador Hydro (NLH)
Supply and Demand Status Report Filed Friday, October 16, 2026
Actual 24 Hour System Performance For Thursday, October 15, 2026
Peak Island System Demand = 600 MW @ 1200
Section 2
Island System Supply:4 1 ,180 MW
NLH Island Generation:3,7,10 1 ,000 MW
NLH Island Power Purchases:5 1 00 MW
NP and CBPP Owned Generation: 1 00 MW
LIL Net Imports to Island:9 ( 20)MW
7-Day Island Peak Demand Forecast: 9 00 MW
'''+rows+'''
Section 3
Island Peak Demand11 12:00 600 MW
Exports at Peak 20 MW
LIL Net Imports to Island 1,234 MWh
Forecast Island Peak Demand 900 MW
'''

def parsed():return dict(parse_text(report_text(),'2026-10-16'),chart=None,chart_error='No supported vectors')

def test_exact_tables_signed_imports_filing_date_and_crosschecks():
    d=parsed();assert d['outlook']['lil-import']==-20 and d['lil_energy_mwh']==1234
    assert d['peak_time']=='12:00' and len(d['forecast'])==7
    assert parse_text(report_text().replace('( 20)MW','- MW'),'2026-10-16')['outlook']['lil-import'] is None
    text=report_text().replace('Report Filed Friday, October 16','Report Filed Monday, October 19')
    assert parse_text(text,'2026-10-16')['filed_date']=='2026-10-19'
    for old,new in [('1 ,180','1 ,1810'),('7-Day Island Peak Demand Forecast: 9 00','7-Day Island Peak Demand Forecast: 9 01'),('12:00 600','12:00 601'),('Thursday, October 15','Wednesday, October 14'),('900 850','900')]:
        with pytest.raises(ValueError):parse_text(report_text().replace(old,new),'2026-10-16')

class FakePage:
    width=612;height=792
    def __init__(self):
        self.curves=[];self.lines=[];self.words=[]
        for y in range(80,241,16):
            value=2200-(y-80)*12.5
            self.lines.append(dict(x0=116,x1=492,top=y,bottom=y))
            self.words.append(dict(text=str(int(value)),x0=99,x1=113,top=y-3,bottom=y+3))
        for key,(color,label) in SERIES.items():
            value=600 if key=='island-demand' else 1200
            self.curves.append(dict(x0=118,x1=490,top=80+(2200-value)/12.5,bottom=80+(2200-value)/12.5,stroking_color=color,pts=[(118+i*372/288,80+(2200-value)/12.5) for i in range(289)]))
    def filter(self,fn):return self
    def extract_words(self):return self.words

def test_vectors_calibrated_and_refuse_wrong_peak_missing_curve_or_legend():
    p=FakePage();text=' '.join(v[1] for v in SERIES.values());r=parsed()
    d=parse_chart(p,r,text);assert len(d['series'])==4 and d['approximate']
    assert d['series']['island-demand'][144]=={'minute':720,'mw':600}
    with pytest.raises(ValueError):parse_chart(p,dict(r,peak_mw=900),text)
    with pytest.raises(ValueError):parse_chart(p,r,'renamed legend')
    p.curves.pop()
    with pytest.raises(ValueError):parse_chart(p,r,text)

def test_archive_dedup_revisions_rejection_and_separate_live_history(tmp_path):
    p=PowerReports(tmp_path);url='http://www.pub.nf.ca/applications/IslandInterconnectedSystem/files/reports/2026/10/2026-10-16%20-%20NLH%20-%20Island%20Supply%20and%20Demand%20Report.pdf';r=parsed()
    p.commit(b'original',url,r,1);p.commit(b'original',url,r,2)
    assert p.public()['count']==1 and p.public()['revisions']==1
    p.commit(b'revised',url,dict(r,exports_at_peak_mw=25),3)
    p.attempt(url,4,'New copy rejected')
    restored=PowerReports(tmp_path).public();assert restored['revisions']==2 and restored['latest']['exports_at_peak_mw']==25 and restored['failures']
    with p.connect() as db:
        assert db.execute('select count(*) from pub_values').fetchone()[0]==23
        assert db.execute('select value from pub_values where metric="lil-import"').fetchone()[0]==-20
    assert image(restored,'power-history').size==(3840,2160)
    assert image(restored,'power-report').size==(3840,2160)

def test_url_pdf_and_response_bounds():
    base='http://www.pub.nf.ca/applications/IslandInterconnectedSystem/files/reports/2026/10/2026-10-16 - NLH - Island Supply and Demand Report.pdf'
    assert str(report_date(base))=='2026-10-16'
    for url in (base.replace('www.pub.nf.ca','example.com'),base+'?url=secret',base.replace('/2026/10/','/2025/10/'),base.replace('http://','file://')):
        with pytest.raises(ValueError):report_date(url)
    with pytest.raises(ValueError):parse_pdf(b'not pdf','2026-10-16')
    async def bounded():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'123456'))) as c:
            with pytest.raises(ValueError):await fetch(c,base,5)
    asyncio.run(bounded())
