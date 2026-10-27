import json
from pathlib import Path
from skycam.weather import Weather,parse_weather
from skycam.weather_renderer import WeatherRenderer
from skycam import playout
import pytest
from skycam.weather_renderer import condition_kind

@pytest.mark.parametrize('text,expected',[
    ('Light Rain','rain'),('Chance of rain showers or flurries','mixed'),
    ('Freezing rain','mixed'),('Thunderstorms','thunder'),('Fog patches','fog'),
    ('Partly cloudy','partly'),('Clear','clear'),('Observation unavailable','unknown')])
def test_weather_symbols_do_not_invent_conditions(text,expected):
    assert condition_kind(text)==expected

def fixture():return json.loads((Path(__file__).parent/'fixtures/weather-synthetic.json').read_text(encoding='utf-8-sig'))

def test_official_schema_units_and_missing_visibility():
    parsed=parse_weather(fixture())
    assert parsed['temperature_c']==5.1 and parsed['wind_kmh']==15 and parsed['gust_kmh']==36
    assert parsed['visibility_km'] is None
    assert parsed['forecasts'][0]['period']=='Tonight'
    assert parsed['observed_at'] and parsed['forecast_at']

def test_observation_expiry_hides_values_including_future_data(tmp_path):
    w=Weather(tmp_path);w.data=parse_weather(fixture());now=w.data['observed_at']+10;w.fetched_at=now
    assert w.public(now)['current_available']
    assert not w.public(now+7201)['current_available'] and w.public(now+7201)['temperature_c'] is None
    assert not w.public(now-600)['current_available']
    w.data['observed_at']=now-7500;w.fetched_at=now
    assert not w.public(now)['current_available']

def test_expired_forecast_hidden_and_bad_qa_not_reported(tmp_path):
    raw=fixture();raw['properties']['currentConditions']['temperature']['qaValue']['en']=0
    w=Weather(tmp_path);w.data=parse_weather(raw);now=w.data['forecast_at']+43201;w.fetched_at=now
    assert w.data['temperature_c'] is None
    assert not w.public(now)['forecasts']

def test_failed_fetch_keeps_last_cache_with_notice(monkeypatch,tmp_path):
    w=Weather(tmp_path);w.data=parse_weather(fixture());now=w.data['observed_at']+10;w.fetched_at=now
    class Broken:
        def __init__(self,*a,**k):raise OSError('offline')
    monkeypatch.setattr('skycam.weather.httpx.Client',Broken);w.fetch()
    assert w.public(now)['cached'] and w.public(now)['temperature_c']==5.1
    cold=Weather(tmp_path);cold.fetch();assert not cold.public(now)['current_available']

def test_weather_fallback_renders_and_refresh_is_bounded(monkeypatch,tmp_path):
    monkeypatch.setattr(playout,'ENABLED',False)
    w=Weather(tmp_path);r=WeatherRenderer(tmp_path,w);r.tick()
    assert r.status['ready'] and (r.frames/'preview.jpg').exists()
    sequence=r.seq;r.ensure();assert r.seq==sequence
