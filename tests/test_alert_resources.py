import base64
import hashlib
import json
import time
import xml.etree.ElementTree as ET

import httpx
import pytest

from skycam.alert_resources import allowed_url, fetch_resource, resources, validate_bytes
from skycam.alerts import Alerts, HOSTS, NS
from skycam.alert_presentation import AlertPresentation
from tests.test_alerts import message, NOW


def row(data=b'fixture'):
    return {'digest': hashlib.sha1(data).hexdigest(), 'size': len(data),
            'inline': base64.b64encode(data).decode(), 'uri': ''}


def test_resource_integrity_and_urls():
    assert validate_bytes(b'fixture', row()) == b'fixture'
    for bad in [{**row(), 'digest': '0'*40}, {**row(), 'size': 1}, {**row(), 'digest': ''}]:
        with pytest.raises(ValueError): validate_bytes(b'fixture', bad)
    for url in ['file:///etc/passwd', 'http://issuer.test/audio', 'https://evil.test/audio',
                'https://issuer.test:8080/a', 'https://user@issuer.test/a']:
        with pytest.raises(ValueError): allowed_url(url, {'issuer.test'})
    assert allowed_url('https://issuer.test/a', {'issuer.test'})


def test_resource_selection_language_and_inline_fallback():
    raw=message().replace(b'</info>', b'''<resource><resourceDesc>Broadcast Audio</resourceDesc>
        <mimeType>audio/mpeg</mimeType><uri>https://issuer.test/a</uri></resource>
        <resource><resourceDesc>Other recording</resourceDesc><mimeType>audio/mpeg</mimeType></resource></info>''')
    info=ET.fromstring(raw).find('c:info',NS)
    assert len(resources(info,NS))==1
    transport=httpx.MockTransport(lambda _:httpx.Response(503))
    with httpx.Client(transport=transport) as client:
        r={**row(), 'uri':'https://issuer.test/a'}
        assert fetch_resource(r,client,{'issuer.test'},time.monotonic()+5)==b'fixture'


def test_minor_update_only_inherits_completed_language(tmp_path):
    alerts=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    alerts.ingest(message(immediate='yes'),HOSTS[0],NOW)
    state=lambda:alerts.public(NOW+30)
    p=AlertPresentation(tmp_path,state,None)
    assert p.frame(NOW)['mode']=='full'
    assert p.frame(NOW+23)['mode']=='summary'
    raw=message('two',kind='Update',references='test-issuer,one,2026-10-17T15:00:00Z',immediate='yes')
    minor=b'<parameter><valueName>profile:CAP-CP:1.0:MinorChange</valueName><value>correction</value></parameter>'
    alerts.ingest(raw.replace(b'</info>',minor+b'</info>'),HOSTS[0],NOW+25)
    assert alerts.public(NOW+25)['immediate'][0]['minor_update']
    assert p.frame(NOW+26)['mode']=='summary'
    # Restart retains the original completed-language evidence.
    p=AlertPresentation(tmp_path,state,None)
    assert p.frame(NOW+27)['mode']=='summary'
    # An excluded language must not create a new presentation.
    french={**alerts.public(NOW+26)['immediate'][0],'language':'fr-CA'}
    p.alerts=lambda:{'immediate':[french],'fresh':True}
    assert p.frame(NOW+28) is None


def test_minor_change_without_prior_presentation_is_new(tmp_path):
    alerts=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    raw=message('two',kind='Update',references='test-issuer,missing,2026-10-17T15:00:00Z',immediate='yes')
    raw=raw.replace(b'</info>',b'<parameter><valueName>profile:CAP-CP:1.0:MinorChange</valueName><value>text</value></parameter></info>')
    alerts.ingest(raw,HOSTS[0],NOW)
    p=AlertPresentation(tmp_path,lambda:alerts.public(NOW),None)
    assert p.frame(NOW)['mode']=='full'


def test_pending_audio_cannot_play_after_cancel(tmp_path):
    class Audio:
        def __init__(self):self.plays=0;self.stops=0
        def prepare(self,*args):pass
        def ready(self,*args):return False
        def public(self):return {}
        def stop(self):self.stops+=1
        def play(self,*args):self.plays+=1
    alerts=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    alerts.ingest(message(immediate='yes'),HOSTS[0],NOW)
    audio=Audio();p=AlertPresentation(tmp_path,lambda:alerts.public(NOW),None,audio)
    p.frame(NOW);p.frame(NOW+1)
    alerts.ingest(message('cancel',kind='Cancel',references='test-issuer,one,2026-10-17T15:00:00Z'),HOSTS[0],NOW+2)
    audio.ready=lambda *_:True
    assert p.frame(NOW+3) is None and audio.plays==0 and audio.stops==1


def test_changed_trust_invalidates_cached_verification(tmp_path,monkeypatch):
    monkeypatch.setattr('skycam.alerts.time.time',lambda:NOW)
    a=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    a.ingest(message(),HOSTS[0],NOW);a.persist()
    monkeypatch.setattr('skycam.alerts.policy_fingerprint',lambda:'new-policy')
    b=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    assert not b.items and b.pending


def test_supplied_audio_decodes_authenticated_inline_wav(tmp_path):
    import io
    import wave
    import numpy as np
    from skycam.alert_resources import supplied_audio
    buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setparams((1,2,48000,0,'NONE','not compressed'))
        wav.writeframes((np.sin(np.arange(9600)*2*np.pi*440/48000)*2000).astype('<i2').tobytes())
    resource={**row(buf.getvalue()),'mime_type':'audio/wav'}
    alert={'verification':{'verified':True},'audio_resources':[resource]}
    audio,error=supplied_audio(alert,tmp_path,'fixture')
    assert error is None and len(audio)==9600 and np.isfinite(audio).all()
    resource['digest']='0'*40
    audio,error=supplied_audio(alert,tmp_path,'fixture')
    assert audio is None and 'local speech' in error
    assert not list(tmp_path.glob('*.resource'))
