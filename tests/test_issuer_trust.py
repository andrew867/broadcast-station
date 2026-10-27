from datetime import datetime, timedelta, timezone
import json

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner

from skycam.issuer_trust import verify_issuer, policy_fingerprint
from tests.test_alerts import message


def signed_fixture(tmp_path, monkeypatch, before_days=-1, after_days=1):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Off-air fixture only')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now+timedelta(days=before_days))
          .not_valid_after(now+timedelta(days=after_days)).sign(key,hashes.SHA256()))
    pem=cert.public_bytes(serialization.Encoding.PEM)
    (tmp_path/'fixture.pem').write_bytes(pem)
    config=tmp_path/'trust.json'
    config.write_text(json.dumps({'issuers':{'test-issuer':{'certificate':'fixture.pem'}}}))
    monkeypatch.setenv('SKYCAM_ISSUER_TRUST',str(config))
    signed=XMLSigner().sign(etree.fromstring(message()),key=key,cert=pem)
    return etree.tostring(signed)


def test_pinned_signature_valid_and_tampering_rejected(tmp_path,monkeypatch):
    packet=signed_fixture(tmp_path,monkeypatch)
    assert verify_issuer(packet)['verified']
    with pytest.raises(Exception):verify_issuer(packet.replace(b'OFF-AIR TEST ONLY',b'Altered payload'))
    with pytest.raises(Exception):verify_issuer(packet.replace(b'URI=""',b'URI="#partial"'))
    with pytest.raises(Exception):verify_issuer(message())
    old=policy_fingerprint();(tmp_path/'fixture.pem').write_bytes(b'broken')
    assert policy_fingerprint()!=old
    with pytest.raises(Exception):verify_issuer(packet)


def test_unconfigured_is_not_claimed_verified(monkeypatch):
    monkeypatch.delenv('SKYCAM_ISSUER_TRUST',raising=False)
    assert verify_issuer(message())=={'status':'not_configured','verified':False}


def test_naads_wrapper_removed_only_after_separate_dss_gate(tmp_path,monkeypatch):
    packet=signed_fixture(tmp_path,monkeypatch)
    root=etree.fromstring(packet)
    etree.SubElement(root,'{http://www.w3.org/2000/09/xmldsig#}Signature',Id='NAADS Signature')
    assert verify_issuer(etree.tostring(root))['verified']
    # An extra issuer signature is ambiguous and rejected.
    etree.SubElement(root,'{http://www.w3.org/2000/09/xmldsig#}Signature',Id='other')
    with pytest.raises(ValueError):verify_issuer(etree.tostring(root))


@pytest.mark.parametrize('before,after',[(-3,-1),(1,3)])
def test_expired_and_not_yet_valid_pins_are_rejected(tmp_path,monkeypatch,before,after):
    packet=signed_fixture(tmp_path,monkeypatch,before,after)
    from signxml.exceptions import InvalidCertificate
    with pytest.raises(InvalidCertificate):verify_issuer(packet)


def test_renewal_rejects_old_signature_and_changes_cache_policy(tmp_path,monkeypatch):
    old=signed_fixture(tmp_path,monkeypatch);fingerprint=policy_fingerprint()
    new=signed_fixture(tmp_path,monkeypatch)
    assert policy_fingerprint()!=fingerprint
    assert verify_issuer(new)['verified']
    with pytest.raises(Exception):verify_issuer(old)


def test_overlapping_renewal_then_local_revocation(tmp_path,monkeypatch):
    from skycam.issuer_trust import certificate_fingerprint
    old=signed_fixture(tmp_path,monkeypatch)
    old_pem=(tmp_path/'fixture.pem').read_bytes()
    (tmp_path/'old.pem').write_bytes(old_pem)
    new=signed_fixture(tmp_path,monkeypatch)
    entry={'certificates':['old.pem','fixture.pem']}
    policy={'require_all':True,'issuers':{'test-issuer':entry}}
    path=tmp_path/'trust.json';path.write_text(json.dumps(policy))
    assert verify_issuer(old)['verified'] and verify_issuer(new)['verified']
    before=policy_fingerprint()
    entry['revoked_sha256']=[certificate_fingerprint(old_pem).upper()]
    path.write_text(json.dumps(policy))
    assert policy_fingerprint()!=before
    with pytest.raises(Exception):verify_issuer(old)
    assert verify_issuer(new)['verified']
    entry['disabled']=True;path.write_text(json.dumps(policy))
    with pytest.raises(ValueError,match='disabled'):verify_issuer(new)


@pytest.mark.parametrize('bad',[[],{}, {'issuers':[]},
    {'issuers':{},'require_all':'false'},
    {'issuers':{'test-issuer':{'certificate':'fixture.pem','disabled':'false'}}},
    {'issuers':{'test-issuer':{'certificates':[]}}},
    {'issuers':{'test-issuer':{'certificate':'fixture.pem','revoked_sha256':['invalid']}}}])
def test_invalid_policy_fails_closed(tmp_path,monkeypatch,bad):
    packet=signed_fixture(tmp_path,monkeypatch)
    (tmp_path/'trust.json').write_text(json.dumps(bad))
    assert policy_fingerprint()=='invalid-policy'
    with pytest.raises(ValueError):verify_issuer(packet)


def test_required_unknown_sender_and_certificate_path_escape(tmp_path,monkeypatch):
    packet=signed_fixture(tmp_path,monkeypatch)
    policy=tmp_path/'trust.json'
    policy.write_text(json.dumps({'require_all':True,'issuers':{}}))
    with pytest.raises(ValueError,match='no configured'):verify_issuer(packet)
    policy.write_text(json.dumps({'issuers':{'test-issuer':{'certificate':'../outside.pem'}}}))
    assert policy_fingerprint()=='invalid-policy'
    with pytest.raises(ValueError,match='inside the trust folder'):verify_issuer(packet)
