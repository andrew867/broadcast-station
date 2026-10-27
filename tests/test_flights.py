from datetime import datetime,timedelta
from pathlib import Path
import pytest
from skycam.flights import Flights,parse_table,TZ

def html(date='31 Dec',scheduled='23:55',revised='',status='Delayed'):
    values={'airline':'Example Air','flight-num':'ZZ123','date':date,'time':scheduled,'revised':revised,'city':'Test City','status':status}
    return '<table class="tblData"><tr>'+''.join(f'<td class="{key}">{v}</td>' for key,v in values.items())+'</tr></table>'

def test_parse_year_boundary_and_revised_missing():
    now=datetime(2027,1,1,0,15,tzinfo=TZ)
    row=parse_table(html(),now)[0]
    assert row['scheduled_at'].startswith('2026-12-31T23:55')
    assert row['revised']=='' and row['status']=='Delayed'
    assert parse_table(html('1 Jan'),datetime(2026,12,31,23,tzinfo=TZ))[0]['scheduled_at'].startswith('2027-01-01')
    for broken in ['<html>Maintenance</html>',html().replace('23:55','25:15'),html().replace('31 Dec','12 Nope'),html().replace('class="city"','class="unknown"')]:
        with pytest.raises(ValueError):parse_table(broken,now)
    with pytest.raises(ValueError):parse_table(html('1 Jan'),datetime(2026,10,17,tzinfo=TZ))

def test_cache_expiry_partial_error_and_delayed_flight(tmp_path):
    flights=Flights(tmp_path);now=datetime(2027,1,1,2,15,tzinfo=TZ)
    flights.boards['arrivals']={'rows':parse_table(html(),now),'checked_at':now.timestamp(),'error':None}
    assert len(flights.public('arrivals',now.timestamp())['rows'])==1  # Still delayed, not dropped after an hour.
    flights.boards['arrivals']['error']='Network timeout'
    assert flights.public('arrivals',now.timestamp()+10)['cached']
    expired=flights.public('arrivals',now.timestamp()+1801)
    assert not expired['available'] and expired['rows']==[]
    assert not flights.public('departures',now.timestamp())['available']
    with pytest.raises(ValueError):flights.public('../bad')

def test_fetch_failures_preserve_last_good_then_expire(tmp_path,monkeypatch):
    import skycam.flights as module
    flights=Flights(tmp_path);now=datetime(2027,1,1,0,15,tzinfo=TZ)
    flights.boards['arrivals']={'rows':parse_table(html(),now),'checked_at':now.timestamp(),'html':html(),'error':None}
    def fail(*a,**kw):raise OSError('Offline')
    monkeypatch.setattr(module.httpx,'Client',fail)
    flights.fetch()
    assert flights.public('arrivals',now.timestamp()+5)['cached']
    restored=Flights(tmp_path)
    assert len(restored.public('arrivals',now.timestamp()+5)['rows'])==1

def test_board_pagination_cache_and_offline_image(tmp_path):
    from skycam.community_cards import CommunityCards
    from PIL import Image
    flights=Flights(tmp_path);now=datetime(2027,1,1,0,15,tzinfo=TZ)
    row=parse_table(html('1 Jan','01:00'),now)[0]
    flights.boards['arrivals']={'rows':[dict(row,**{'flight-num':f'ZZ{i}'}) for i in range(8)],'checked_at':now.timestamp(),'error':None}
    cards=CommunityCards(tmp_path,flights)
    first=cards.path('yyt-arrivals',now)
    assert cards.path('yyt-arrivals',now+timedelta(seconds=18))!=first
    page0=cards.path('yyt-arrivals',now,page_override=0)
    assert cards.path('yyt-arrivals',now+timedelta(seconds=18),page_override=0)==page0
    assert Image.open(cards.path('yyt-departures',now)).size==(3840,2160)
