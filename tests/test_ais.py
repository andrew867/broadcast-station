from pathlib import Path
import json
from skycam.ais import Ais,AisConfig,timestamp
import pytest

NOW=1792351300
def report(at='2026-10-18 19:21:40.893699231 +0000 UTC',mmsi=316023651):
    return {'MessageType':'PositionReport','MetaData':{'MMSI':mmsi,'ShipName':'BEN VIKING','time_utc':at},
        'Message':{'PositionReport':{'UserID':mmsi,'Valid':True,'Latitude':47.56301,'Longitude':-52.70634,
                                   'Sog':0,'Cog':352.1,'TrueHeading':215}}}

def test_timestamp_and_real_format(tmp_path):
    assert timestamp('2026-10-18 19:21:40.893699231 +0000 UTC')==pytest.approx(NOW+.893699)
    a=Ais(tmp_path);a.ingest(report(),NOW+2);v=a.public(NOW+3)['vessels'][0]
    assert v['name']=='BEN VIKING' and v['sog']==0 and v['heading']==215 and not v['stale']
    assert a.public(NOW+302)['vessels'][0]['stale']
    assert not a.public(NOW+1802)['vessels']
    with pytest.raises(ValueError):timestamp('2026-10-18 19:21:40')

def test_bad_positions_sentinels_and_order(tmp_path):
    a=Ais(tmp_path);r=report();r['Message']['PositionReport']['TrueHeading']=511
    r['Message']['PositionReport']['Sog']=102.3;a.ingest(r,NOW+1)
    v=a.public(NOW+2)['vessels'][0];assert v['heading'] is None and v['sog'] is None
    r['Message']['PositionReport']['Latitude']=91
    with pytest.raises(ValueError):a.ingest(r,NOW+2)
    r=report();r['Message']['PositionReport']['Valid']=False
    with pytest.raises(ValueError):a.ingest(r,NOW+2)
    with pytest.raises(ValueError):a.ingest(report(),NOW+1802)
    r=report();r['Message']['PositionReport']['Latitude']=47.6;a.ingest(r,NOW+3)
    assert a.public(NOW+3)['vessels'][0]['lat']==47.56301

def test_static_metadata_does_not_refresh_position_and_secret_not_public(tmp_path,monkeypatch):
    monkeypatch.setenv('AISSTREAM_API_KEY','fixture-secret')
    a=Ais(tmp_path);a.ingest(report(),NOW+2)
    r=report('2026-10-18T19:26:50Z');r['MessageType']='ShipStaticData'
    r['Message']={'ShipStaticData':{'UserID':316023651,'Valid':True,'Name':'BEN VIKING','CallSign':'TEST','Type':70}}
    a.ingest(r,NOW+312);d=a.public(NOW+312)
    assert d['vessels'][0]['stale'] and 'fixture-secret' not in json.dumps(d)
    a.save(AisConfig(show_on_maps=True));assert 'fixture-secret' not in a.path.read_text()
    a.save(AisConfig(enabled=False));assert not a.public(NOW+312)['vessels']

def test_bounded_vessels_and_trail_break(tmp_path):
    from datetime import datetime,timezone
    a=Ais(tmp_path)
    for i in range(510):a.ingest(report(mmsi=316000000+i),NOW+1)
    assert len(a.vessels)==500
    a=Ais(tmp_path)
    for i in range(80):
        at=NOW+i*16;r=report(datetime.fromtimestamp(at,timezone.utc).isoformat())
        r['Message']['PositionReport']['Longitude']+=i*.0001;a.ingest(r,at+1)
    assert len(a.public(NOW+1265)['vessels'][0]['trail'])<=40
    r=report(datetime.fromtimestamp(NOW+1500,timezone.utc).isoformat());a.ingest(r,NOW+1501)
    assert len(a.public(NOW+1501)['vessels'][0]['trail'])==1


def test_static_only_packets_never_create_or_refresh_map_positions(tmp_path):
    a=Ais(tmp_path);r=report();r['MessageType']='ShipStaticData'
    r['Message']={'ShipStaticData':{'UserID':316023651,'Valid':True,'Name':'BEN VIKING'}}
    r['MetaData'].update(Latitude=46.7,Longitude=-48.5)
    a.ingest(r,NOW+1)
    d=a.public(NOW+2)
    assert d['counts']['recent']==0 and d['vessels']==[]
    assert d['diagnostics']['static_only_recent']==1
    assert d['diagnostics']['validated_messages_by_type']=={'ShipStaticData':1}
    a.ingest(report(),NOW+2);a.ingest(report(),NOW+3)
    d=a.public(NOW+4)
    assert d['counts']['recent']==1 and d['diagnostics']['position_updates_applied']==1
    assert d['diagnostics']['duplicate_or_older_positions']==1
    assert d['diagnostics']['static_only_recent']==0


def test_long_range_report_sentinels_and_fresh_detail_priority(tmp_path):
    from skycam.ais import LONG_RANGE,POSITION_TYPES
    assert LONG_RANGE in POSITION_TYPES
    a=Ais(tmp_path);r=report();r['MessageType']=LONG_RANGE
    p=r['Message'].pop('PositionReport');p.update(Sog=63,Cog=511,PositionLatency=True)
    p.pop('TrueHeading');r['Message'][LONG_RANGE]=p
    a.ingest(r,NOW+1);v=a.public(NOW+2)['vessels'][0]
    assert v['long_range'] and v['position_latency'] and v['sog'] is None and v['cog'] is None
    assert v['heading'] is None and v['trail']==[]
    detailed=report('2026-10-18T19:21:50Z');a.ingest(detailed,NOW+11)
    assert not a.public(NOW+12)['vessels'][0]['long_range']
    r['MetaData']['time_utc']='2026-10-18T19:22:00Z';p['Longitude']=-48;p['Sog']=0;p['Cog']=0
    a.ingest(r,NOW+21)
    assert a.public(NOW+22)['vessels'][0]['lon']==-52.70634
    r['MetaData']['time_utc']='2026-10-18T19:27:00Z';a.ingest(r,NOW+321)
    v=a.public(NOW+322)['vessels'][0]
    assert v['long_range'] and v['lon']==-48 and v['sog']==0
    assert a.public(NOW+322)['position_types'][LONG_RANGE]==3
