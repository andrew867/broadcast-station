from datetime import datetime,timezone,timedelta,date
import math
import pytest
from skycam import daylight
from skycam.moon_card import public as lunar_public,image as lunar_image
from skycam.live_markets import LiveMarkets,MAX_AGE
from skycam.markets import Markets
from skycam.market_graphics import image,trend_points,movement


def trade(live,at,price,symbol='OANDA:WTICO_USD'):
    live.ingest({'type':'trade','data':[{'s':symbol,'p':price,'t':at*1000}]},at)


def test_missing_calendar_moonset_shows_dated_next_event():
    now=datetime(2026,10,19,14,tzinfo=timezone.utc)
    data=lunar_public(now)
    assert data['moonset'] is None
    assert data['next_moonset']=='2026-10-20T00:44:00-02:30'
    display=daylight.lunar_display(data,'moonset')
    assert display=={'time':'12:44 AM','date':'TOMORROW / OCT 20 NDT','next':True}
    assert daylight.public(now)['next_moonset']==data['next_moonset']
    assert lunar_image(data).size==(3840,2160)


def test_lunar_schedule_rollover_dst_and_explicit_unavailable(monkeypatch):
    now=datetime(2026,11,1,12,tzinfo=timezone.utc)
    data=lunar_public(now)
    for key in ['moonrise','moonset']:
        at=data['next_'+key]
        assert at and datetime.fromisoformat(at).timestamp()>now.timestamp()
        assert daylight.lunar_display(data,key)['date'].endswith('NST')
    monkeypatch.setattr(daylight,'lunar_events',lambda day:{'moonrise':None,'moonset':None})
    none={'date':'2026-11-01',**daylight.lunar_schedule(now)}
    assert daylight.lunar_display(none,'moonset')['time']=='Unavailable'


def test_history_compares_same_instrument_and_resets_after_gap():
    live=LiveMarkets('')
    trade(live,1000,100);trade(live,1006,102);trade(live,1012,101)
    row=live.public(1012)['quotes']['wti']
    assert row['change']==-1 and row['window_change']==1 and row['window_percent']==1
    assert row['window_start_at']==1000 and len(row['history'])==3
    trade(live,1011,999)
    assert live.public(1012)['quotes']['wti']['value']==101
    trade(live,1012+MAX_AGE+1,104)
    row=live.public(1012+MAX_AGE+1)['quotes']['wti']
    assert row['change'] is None and row['window_change'] is None and len(row['history'])==1


def test_fx_direction_is_for_displayed_cad_not_raw_usd_pair():
    live=LiveMarkets('');trade(live,1000,1.4,'OANDA:USD_CAD');trade(live,1006,1.5,'OANDA:USD_CAD')
    row=live.public(1006)['quotes']['fx']
    assert row['window_change']==pytest.approx(1/1.5-1/1.4)
    assert row['window_percent']==pytest.approx(((1/1.5)/(1/1.4)-1)*100)
    assert movement(row['window_change'])[0]=='down'


def test_history_is_bounded_and_returned_copy_cannot_mutate_feed():
    live=LiveMarkets('')
    for i in range(2000):trade(live,1000+i,80+i*.001)
    row=live.public(2999)['quotes']['wti']
    assert 2<=len(row['history'])<=121
    assert all(2999-p['at']<=600 for p in row['history'])
    row['history'][0]['value']=9999
    assert live.public(2999)['quotes']['wti']['history'][0]['value']!=9999
    assert live.public(4000)['quotes']['wti']['history']==[]


def test_daily_fallback_never_uses_cfd_window_or_price_baseline(tmp_path):
    now=datetime(2026,10,19,14,tzinfo=timezone.utc).timestamp()
    m=Markets(tmp_path);m.live=LiveMarkets('')
    m.values={'wti':{'checked_at':now,'rows':[{'date':'2026-10-15','value':80},{'date':'2026-10-16','value':82}]}}
    trade(m.live,now-6,100);trade(m.live,now,99)
    live=m.public(now)['cards'][1]
    assert not live['daily_reference'] and live['window_change']==-1
    row=m.public(now+MAX_AGE+1)['cards'][1]
    assert row['daily_reference'] and row['value']==82 and row['change']==2
    assert row['change_percent']==2.5 and row['previous_date']=='2026-10-15'
    assert 'window_change' not in row
    assert [p['value'] for p in row['history']]==[80,82]
    assert image(m.public(now+MAX_AGE+1)).size==(3840,2160)


def test_trend_uses_time_spacing_flat_series_and_missing_data():
    box=(100,200,500,400)
    points,low,high=trend_points([{'at':10,'value':2},{'at':11,'value':2},{'at':20,'value':2}],box)
    assert [p[0] for p in points]==[100,140,500]
    assert all(200<=p[1]<=400 for p in points)
    assert low==high==2
    assert trend_points([],box)==([],None,None)
    assert movement(0)[0]=='flat' and movement(None)[0]=='unknown'


def test_market_three_pages_share_existing_slot():
    from skycam.community_cards import market_page
    for seconds in (5,20,30,45,60):
        assert [market_page(seconds*r,seconds) for r in (0,.34,.67,1,2)]==[0,1,2,2,2]
    assert [market_page(t) for t in (0,10,20,30)]==[0,1,2,0]


def test_timing_tracks_scheduled_block_and_manual_hold(tmp_path,monkeypatch):
    from skycam import rundown
    from skycam.rundown import Rundown,RundownConfig,Cue
    monkeypatch.setattr(rundown.time,'monotonic',lambda:100)
    r=Rundown(tmp_path,lambda *args:None)
    r.config=RundownConfig(cues=[Cue(camera='markets',seconds=30)])
    r.enabled=True;r.deadline=120
    assert r.scene_timing('markets')=={'seconds':30,'elapsed':10}
    r.block={'name':'Information','include_alerts':False,'rule_id':'test','scheduled_at':0,
             'config':RundownConfig(cues=[Cue(camera='markets',seconds=60)])}
    assert r.scene_timing('markets')=={'seconds':60,'elapsed':40}
    assert r.deadline==120
    r.enabled=False
    assert r.scene_timing('markets') is None


def test_expanded_symbols_expire_and_all_three_pages_render(tmp_path):
    from skycam.live_markets import SYMBOLS,METALS,STOCKS
    from skycam.community_cards import markets_image
    m=Markets(tmp_path);m.live=LiveMarkets('')
    for symbol in SYMBOLS:
        trade(m.live,1000,2 if symbol=='OANDA:USD_CAD' else 100,symbol)
        trade(m.live,1006,2.1 if symbol=='OANDA:USD_CAD' else 101,symbol)
    data=m.public(1006)
    assert len(data['cards'])==11
    assert all(c['available'] for c in data['cards'])
    assert data['pages'][1:]==[list(METALS),list(STOCKS)]
    for page in range(3):assert markets_image(data,page).size==(3840,2160)
    stale=m.public(1006+MAX_AGE+1)
    for row in stale['cards'][3:]:
        if row['id'] in STOCKS:
            assert row['available'] and row['fresh'] and row['value']==101
        else:
            assert not row['available'] and row['value'] is None and row['history']==[]


def test_market_watcher_takes_three_pages_inside_25_seconds(tmp_path,monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from skycam import community_cards as cc,playout
    elapsed=[0.];takes=[]
    cards=cc.CommunityCards(tmp_path)
    cards.market_timing=lambda:{'seconds':25,'elapsed':elapsed[0]}
    cards.path=lambda scene,page_override:tmp_path/f'page-{page_override}.png'
    monkeypatch.setattr(playout,'_camera','markets')
    monkeypatch.setattr(playout,'_bank',10)
    monkeypatch.setattr(playout,'STATUS',{'ready':True})
    monkeypatch.setattr(playout,'command',lambda cmd:takes.append((elapsed[0],cmd)))
    monkeypatch.setattr(cc,'time',SimpleNamespace(monotonic=lambda:elapsed[0]))
    async def sleep(seconds):
        elapsed[0]+=seconds
        if elapsed[0]>=25:raise asyncio.CancelledError
    monkeypatch.setattr(cc,'asyncio',SimpleNamespace(to_thread=asyncio.to_thread,sleep=sleep))
    async def run():
        with pytest.raises(asyncio.CancelledError):await cards.watch()
    asyncio.run(run())
    assert [t for t,_ in takes]==[0,8.5,17]
    assert all(f'page-{i}.png' in cmd for i,(_,cmd) in enumerate(takes))
