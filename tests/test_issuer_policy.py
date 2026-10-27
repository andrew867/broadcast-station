import json
import pytest
from skycam.issuer_trust import read_policy,policy_fingerprint,certificate_path


@pytest.mark.parametrize('policy',[[],{}, {'issuers':[]},
    {'issuers':{},'require_all':'false'},
    {'issuers':{'sender':{'certificate':'a.pem','disabled':'false'}}},
    {'issuers':{'sender':{'certificates':[]}}},
    {'issuers':{'sender':{'certificate':'a.pem','certificates':['a.pem']}}},
    {'issuers':{'sender':{'certificate':'a.pem','revoked_sha256':['invalid']}}}])
def test_policy_rejects_invalid_types_and_ambiguous_pins(tmp_path,monkeypatch,policy):
    path=tmp_path/'policy.json';path.write_text(json.dumps(policy))
    monkeypatch.setenv('SKYCAM_ISSUER_TRUST',str(path))
    with pytest.raises(ValueError):read_policy(path)
    assert policy_fingerprint()=='invalid-policy'


def test_renewal_file_and_revocation_changes_invalidate_cache(tmp_path,monkeypatch):
    path=tmp_path/'policy.json'
    entry={'certificates':['old.pem','new.pem'],'revoked_sha256':[]}
    policy={'issuers':{'sender':entry}}
    path.write_text(json.dumps(policy));(tmp_path/'old.pem').write_bytes(b'old')
    (tmp_path/'new.pem').write_bytes(b'new')
    monkeypatch.setenv('SKYCAM_ISSUER_TRUST',str(path))
    first=policy_fingerprint();assert first!='invalid-policy'
    (tmp_path/'new.pem').write_bytes(b'renewed');second=policy_fingerprint();assert second!=first
    entry['revoked_sha256']=['a'*64];path.write_text(json.dumps(policy))
    assert policy_fingerprint()!=second
    with pytest.raises(ValueError):certificate_path(path,'../outside.pem')
