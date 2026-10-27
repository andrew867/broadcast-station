import json
import xml.etree.ElementTree as ET
import pytest
from skycam.alert_verification import parse_response,request_body,SOAP,SERVICE,DSS,SUCCESS
from skycam.alerts import Alerts,HOSTS
from skycam.alert_graphics import AlertPages,emergency_rows,emergency_image,weather_image
from skycam.rundown import Rundown,RundownConfig,Cue
from skycam.native_ticker import NativeTicker
from skycam.broadcast import Broadcast
from skycam import playout
from tests.test_alerts import message,NOW

def verified(_):return {'verified':True}

def soap(request_id,major=SUCCESS):
    from xml.sax.saxutils import escape
    inner=f'<VerifyResponse xmlns="{DSS}" RequestID="{request_id}"><Result><ResultMajor>{major}</ResultMajor></Result></VerifyResponse>'
    return f'<Envelope xmlns="{SOAP}"><Body><DSSVerifySignedNaadsAlertResponse xmlns="{SERVICE}"><DSSVerifySignedNaadsAlertResult>{escape(inner)}</DSSVerifySignedNaadsAlertResult></DSSVerifySignedNaadsAlertResponse></Body></Envelope>'.encode()

def test_verifier_rejects_missing_or_partial_signature_and_wrong_response():
    with pytest.raises(ValueError):request_body(message(),'request')
    signature=b'<Signature xmlns="http://www.w3.org/2000/09/xmldsig#" Id="NAADS Signature"><SignedInfo><Reference URI="#only-part"/></SignedInfo></Signature>'
    with pytest.raises(ValueError):request_body(message().replace(b'</alert>',signature+b'</alert>'),'request')
    parse_response(soap('request'),'request')
    for response in [soap('other'),soap('request','no'),b'<!DOCTYPE x []>'+soap('request')]:
        with pytest.raises(ValueError):parse_response(response,'request')

def test_unverified_cancel_cannot_remove_verified_alert(tmp_path):
    a=Alerts(tmp_path,verified);a.ingest(message(),HOSTS[0],NOW)
    a.verifier=lambda _: {'verified':False}
    with pytest.raises(ValueError):a.ingest(message('cancel',kind='Cancel',references='test-issuer,one,2026-10-17T15:00:00Z'),HOSTS[0],NOW)
    assert len(a.public(NOW)['alerts'])==1
    assert a.rejected==1 and len(a.pending)==1

def test_nonweather_immediate_and_authoritative_geocodes(tmp_path):
    a=Alerts(tmp_path,verified)
    raw=message('bi',immediate='yes').replace(b'<category>Met</category>',b'<category>Safety</category>')
    a.ingest(raw,HOSTS[0],NOW);assert len(a.public(NOW)['immediate'])==1
    raw=message('away',code='3500000').replace(b'Fixture area',b'Avalon')
    a.ingest(raw,HOSTS[0],NOW);assert not a.public(NOW)['alerts']

def test_followups_do_not_modify_saved_rundown_and_expiry_skips(tmp_path):
    calls=[];r=Rundown(tmp_path,lambda *args:calls.append(args))
    r.save(RundownConfig(cues=[Cue(camera='weather'),Cue(camera='cam1')]))
    before=r.path.read_bytes()
    r.followups=lambda _: [{'camera':'weather-alerts','scene':'standard','seconds':30,'token':str(i)} for i in range(2)]
    r.followup_take=lambda cue:calls.append(cue['token']) or True
    r.followup_valid=lambda token:token!='0'
    r.action('start');r.deadline=0;r.advance_due()
    assert r.interlude['token']=='0' and r.index==0
    r.advance_due();assert r.interlude['token']=='1'
    r.action('next');assert r.index==1 and r.interlude is None
    assert r.path.read_bytes()==before
    r.pause();assert r.followup_queue==[]

def test_empty_alerts_leave_normal_rotation(tmp_path):
    r=Rundown(tmp_path,lambda *_:None);r.save(RundownConfig(cues=[Cue(camera='weather'),Cue(camera='cam1')]))
    r.followups=lambda _:[];r.action('start');r.deadline=0;r.advance_due();assert r.index==1

def alert_row(tmp_path):
    a=Alerts(tmp_path,verified);a.ingest(message('bi',immediate='yes'),HOSTS[0],NOW)
    return a.public(NOW)['immediate'][0]

def test_emergency_only_touches_graphics_and_restores_ticker(tmp_path,monkeypatch):
    row=alert_row(tmp_path);state={'immediate':[row],'fresh':True};calls=[]
    monkeypatch.setattr(playout,'command',lambda command,**kwargs:calls.append(command) or '202 OK')
    monkeypatch.setitem(playout.STATUS,'ready',True)
    b=Broadcast(tmp_path);b.state=b.state.model_copy(update={'scene':'clean','show_ticker':False})
    t=NativeTicker(tmp_path,b,lambda:state);t.tick()
    assert any(c.startswith('PLAY 1-41') for c in calls)
    assert not any(c.startswith(('PLAY 1-10','CLEAR 1-10','PLAY 1-5','CLEAR 1-5','ADD','REMOVE')) for c in calls)
    assert all(21<=int(c.split()[1].split('-')[1])<=41 for c in calls)
    state['immediate']=[];calls.clear();t.tick();assert 'CLEAR 1-41' in calls
    assert t.status['emergency'] is False

def test_long_text_retained_across_pages_and_expiry_neutral(tmp_path):
    row=alert_row(tmp_path);row['description']='Full warning details. '*150+'FINAL INSTRUCTION.'
    from skycam.alert_graphics import page_rows
    pages=page_rows([row]);assert len(pages)>1
    assert 'FINAL INSTRUCTION.' in ' '.join(' '.join(p['lines']) for p in pages)
    assert weather_image(pages[0]).size==(3840,2160)
    assert emergency_image(emergency_rows([row])[0]).size==(3840,636)

def test_unsigned_cache_is_not_adopted(tmp_path):
    path=tmp_path/'broadcast/weather-alerts.json';path.parent.mkdir()
    path.write_text(json.dumps({'items':{'old':{'sender':'issuer','identifier':'old','sent':'2026-10-17T15:00:00Z','blocks':[]}},'seen':[]}))
    a=Alerts(tmp_path,verified);assert not a.items and len(a.pending)==1
