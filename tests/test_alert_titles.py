from copy import deepcopy
from skycam.alert_titles import display_title,headline,display_body
from skycam.alert_graphics import body,identity
from skycam.alerts import Alerts,HOSTS
from tests.test_alerts import message,NOW


def test_display_casing_preserves_punctuation_acronyms_and_apostrophes():
    assert display_title('yellow warning - wind - in effect') == 'Yellow Warning - Wind - In Effect'
    assert display_title("ECCC advisory for St. John's and NL") == "ECCC Advisory for St. John's and NL"
    assert display_title('WIND WARNING') == 'WIND WARNING'
    assert display_title('avertissement jaune - vent - en vigueur','fr-CA') == 'Avertissement jaune - Vent - En vigueur'
    assert display_title("épisode de pluie: l'avertissement demeure",'fr-CA') == "Épisode de pluie: L'avertissement demeure"
    assert display_title('unbekannte sprache','de') == 'unbekannte sprache'


def test_display_does_not_mutate_authenticated_wording_or_identity(tmp_path):
    alerts=Alerts(tmp_path,verifier=lambda _: {'verified':True})
    alerts.ingest(message().replace(b'OFF-AIR TEST ONLY',b'yellow warning - wind - in effect'),HOSTS[0],NOW)
    original=deepcopy(alerts.items)
    a=alerts.public(NOW)['alerts'][0]
    assert a['headline']=='yellow warning - wind - in effect'
    assert a['display_headline']=='Yellow Warning - Wind - In Effect'
    assert alerts.items==original
    raw={k:v for k,v in a.items() if not k.startswith('display_')}
    assert body(a)==body(raw) and identity(a)==identity(raw)
    assert headline({'event':'wind warning'})=='Wind Warning'
    text=a['headline']+'\nKeep this instruction AS ISSUED.'
    assert display_body(text,a)=='Yellow Warning - Wind - In Effect\nKeep this instruction AS ISSUED.'
    assert display_body('do not change a different first line',a)=='do not change a different first line'
