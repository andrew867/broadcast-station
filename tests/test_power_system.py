import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from skycam.power_system import PowerSystem,parse_readings,image,METRICS
from skycam.outages import Outages,parse_hydro,display_rows,outage_image
from skycam.alert_presentation import AlertPresentation,utility_alert
NOW=datetime(2026,10,21,10,0,tzinfo=ZoneInfo('America/St_Johns')).timestamp()
def page(stamp='10/21/2026 10:00 AM'):
    return ''.join(f'<div class="sysgen"><h3>{v[0]}</h3><button>{n} MW </button><p>AS OF <strong>{stamp}</strong></p></div>' for n,v in zip((974,456,3409),METRICS.values()))
def notice(planned=True,**kw):
    row={'Outageid':42,'OutagedateDB':'2026-10-22T10:00:00' if planned else '2026-10-21T09:00:00','RestorationdateDB':'2026-10-22T16:00:00','CustomerAffected':0,'CommunityName':'Example Cove','Title':'Equipment maintenance','OutageLatitude':49.4,'OutageLongitude':-56.1,'OutageReportInfo':'Test only'}
    row.update(kw);return row

def test_named_readings_units_dates_zero_and_ambiguous_clock():
    rows=parse_readings(page(),NOW)
    assert [r['mw'] for r in rows]==[974,456,3409]
    assert all(r['observed_at']==NOW for r in rows)
    assert parse_readings(page().replace('456 MW','0 MW'),NOW)[1]['mw']==0
    for text in (page().replace('974 MW','974 GW'),page().replace('974 MW','-1 MW'),page()+page(),page().replace('Current Island System Demand','Different figure'),page('10/22/2026 10:00 AM')):
        with pytest.raises(ValueError):parse_readings(text,NOW)
    with pytest.raises(ValueError):parse_readings(page('11/01/2026 01:30 AM'),NOW+12*86400)

def test_history_dedup_revision_retention_restart_and_failed_check(tmp_path):
    p=PowerSystem(tmp_path);rows=parse_readings(page(),NOW);p.record(rows,NOW);p.record(rows,NOW+300)
    assert all(len(r['history'])==1 for r in p.public(NOW+300)['readings'])
    rows[0]['mw']=975;p.record(rows,NOW+301)
    assert p.public(NOW+301)['readings'][0]['mw']==975
    with p.connect() as db:db.execute('INSERT INTO readings VALUES(?,?,?)',('island-demand',int(NOW-91*86400),1))
    p.record(rows,NOW+302)
    with p.connect() as db:assert db.execute('SELECT count(*) FROM readings').fetchone()[0]==3
    assert not any(r['fresh'] for r in PowerSystem(tmp_path).public(NOW+302)['readings'])
    p.error='network down';assert not any(r['fresh'] for r in p.public(NOW+302)['readings'])
    assert p.public(NOW+302)['readings'][0]['mw']==975
    assert image(p.public(NOW+302)).size==(3840,2160)

def test_hydro_unknown_counts_and_namespaced_ids():
    planned=parse_hydro([notice()],True,NOW)[0];current=parse_hydro([notice(False)],False,NOW)[0]
    assert planned['customers']==0 and planned['id']!=current['id']
    assert 'customers' not in utility_alert(current,NOW)['description'] and 'Hydro' in utility_alert(current,NOW)['sender']
    assert '. .' not in utility_alert(current,NOW)['description']
    assert '12 customers' in utility_alert(dict(current,customers=12),NOW)['description']
    assert parse_hydro([notice(CustomerAffected=None)],True,NOW)[0]['customers'] is None
    with pytest.raises(ValueError):parse_hydro([notice(CustomerAffected=-1)],True,NOW)
    with pytest.raises(ValueError):parse_hydro({'error':'bad'},True,NOW)

def test_both_utility_planned_rows_never_interrupt_even_while_active(tmp_path):
    from tests.test_outages import feature,parse
    o=Outages(tmp_path);o.rows=parse_hydro([notice()],True,NOW)
    o.rows+=parse([feature(TIME_BEGIN=(NOW-600)*1000,TIME_END=(NOW+1800)*1000)],True,NOW)
    o.checked_at=NOW;o.verified=True;data=o.public(NOW)
    assert len(display_rows(data))==2 and not o.banner(NOW)
    presentation=AlertPresentation(tmp_path,lambda:{'immediate':[]},lambda:o.public(NOW))
    assert presentation.frame(NOW) is None and presentation.candidates(NOW)==[]
    assert outage_image(data,0).size==(3840,2160)
    o.rows+=parse_hydro([notice(False,CustomerAffected=12)],False,NOW)
    assert o.banner(NOW)['total']==1
    assert len(presentation.candidates(NOW))==1
    presentation.frame(NOW);o.rows[-1]['planned']=True
    assert presentation.frame(NOW+1) is None

def test_partial_utility_failure_preserves_other_feed_and_cached_rows(tmp_path,monkeypatch):
    import skycam.outages as mod
    o=Outages(tmp_path);o.rows=parse_hydro([notice(False,CustomerAffected=12)],False,NOW)
    o.feed_status={'hydro-current':{'checked_at':NOW-60,'verified':True,'error':None}}
    async def power(client,layer):return []
    async def hydro(client,planned,now):
        if not planned:raise ValueError('source failed')
        return parse_hydro([notice()],True,NOW)
    monkeypatch.setattr(mod,'fetch_layer',power);monkeypatch.setattr(mod,'fetch_hydro',hydro);monkeypatch.setattr(mod.time,'time',lambda:NOW)
    asyncio.run(o.refresh());data=o.public(NOW)
    assert data['fresh'] and not data['complete'] and len(data['active'])==1
    assert not data['active'][0]['fresh'] and not o.banner(NOW)
    assert len(data['upcoming'])==1 and o.eligible()

def test_scheduled_maintenance_in_current_layer_is_quiet_and_deduplicated(tmp_path):
    from tests.test_outages import feature,parse
    o=Outages(tmp_path)
    o.rows=parse([feature(ID=10,CAUSE='Scheduled Maintenance',TIME_OUTAGE=(NOW-300)*1000,TIME_RESTORED_EST=(NOW+3600)*1000)],False,NOW)
    o.rows+=parse([feature(ID=20,CAUSE='Scheduled Maintenance',TIME_BEGIN=(NOW-600)*1000,TIME_END=(NOW+3600)*1000)],True,NOW)
    o.checked_at=NOW;o.verified=True
    assert len(o.public(NOW)['active'])==1 and o.public(NOW)['active'][0]['planned']
    assert not o.banner(NOW)
    p=AlertPresentation(tmp_path,lambda:{},lambda:o.public(NOW))
    assert p.candidates(NOW)==[]
