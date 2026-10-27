from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from PIL import Image
from skycam import daylight
from skycam.community_cards import CommunityCards, SCENES

def test_solar_order_local_date_and_next_day():
    data=daylight.public(datetime(2026,10,18,1,tzinfo=timezone.utc))
    assert data['date']=='2026-10-17'
    events={k:datetime.fromisoformat(v) for k,v in data['events'].items()}
    assert events['dawn']<events['sunrise']<events['noon']<events['sunset']<events['dusk']
    assert data['phase']=='Night' and data['next_event']=='dawn'
    assert datetime.fromisoformat(data['next_at']).date().isoformat()=='2026-10-18'
    assert 9*3600<data['daylight_seconds']<12*3600
    assert data['change_seconds']<0
    with pytest.raises(ValueError):daylight.public(datetime(2026,10,17))

def test_solar_dst_and_leap_date():
    tz=ZoneInfo(daylight.TIMEZONE)
    for month,day,offset in [(3,7,-3.5),(3,8,-2.5),(10,31,-2.5),(11,1,-3.5)]:
        data=daylight.public(datetime(2026,month,day,12,tzinfo=tz))
        assert datetime.fromisoformat(data['events']['sunrise']).utcoffset()==timedelta(hours=offset)
        assert 0<data['daylight_seconds']<86400
    assert daylight.public(datetime(2028,2,29,12,tzinfo=tz))['date']=='2028-02-29'

def test_card_cache_refresh_repair_and_bound(tmp_path):
    cards=CommunityCards(tmp_path);now=datetime(2026,10,17,16,15,tzinfo=timezone.utc)
    path=cards.path('daylight',now)
    assert cards.path('daylight',now+timedelta(seconds=20))==path
    path.write_bytes(b'')
    assert cards.path('daylight',now).stat().st_size>10000
    assert cards.path('daylight',now+timedelta(minutes=1))!=path
    for i in range(25):(cards.folder/f'daylight-old-{i}.png').write_bytes(b'bad')
    cards.path('daylight',now)
    assert len(list(cards.folder.glob('daylight-*.png')))<=16
    assert Image.open(cards.path('station-info',now)).size==(3840,2160)
    with pytest.raises(ValueError):cards.path('../invalid',now)

def test_cards_catalog_preview_and_no_extra_inputs(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from skycam import app as module, playout
    from skycam.graphics import render
    from skycam.broadcast import BroadcastState
    import skycam.graphics as graphics
    monkeypatch.setattr(module,'community_cards',CommunityCards(tmp_path))
    monkeypatch.setattr(graphics,'DATA',tmp_path)
    client=TestClient(module.app)
    scenes={s['id']:s for s in client.get('/api/scenes').json()}
    for scene in SCENES:
        assert scenes[scene]['kind']=='card' and playout.available(scene)
        assert playout.required(scene)==set()
        response=client.get('/api/maps/'+scene+'/image')
        assert response.status_code==200 and response.headers['content-type']=='image/png'
        # Card owns its entire layout; camera lower thirds must not obscure it.
        overlay=Image.open(render(BroadcastState(camera=scene)))
        assert overlay.getbbox() is None
    assert client.get('/api/daylight').json()['timezone']=='America/St_Johns'
    assert client.get('/api/maps/not-a-scene/image').status_code==404
