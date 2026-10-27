"""Optional pinned issuer signatures, always additional to NAADS DSS.

No certificate, key, endpoint or trust anchor from a received alert is adopted.
Configure an exact sender-to-certificate mapping outside the application tree.
"""
import hashlib
import json
import os
import re
from pathlib import Path

CAP = 'urn:oasis:names:tc:emergency:cap:1.2'
DS = 'http://www.w3.org/2000/09/xmldsig#'


def read_policy(file):
    policy=json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(policy,dict) or not isinstance(policy.get('issuers'),dict):
        raise ValueError('Issuer trust must contain an issuer mapping')
    if type(policy.get('require_all',False)) is not bool:
        raise ValueError('require_all must be true or false')
    for sender,entry in policy['issuers'].items():
        if not isinstance(sender,str) or not sender or not isinstance(entry,dict):
            raise ValueError('Invalid issuer entry')
        if type(entry.get('disabled',False)) is not bool:
            raise ValueError('disabled must be true or false')
        certificate_names(entry)
        revoked=entry.get('revoked_sha256',[])
        if not isinstance(revoked,list) or len(revoked)>100 or any(
                not isinstance(x,str) or not re.fullmatch('[0-9a-fA-F]{64}',x) for x in revoked):
            raise ValueError('Revocations must be SHA256 certificate fingerprints')
    return policy


def certificate_names(entry):
    if 'certificate' in entry and 'certificates' in entry:
        raise ValueError('Use certificate or certificates, not both')
    names=entry.get('certificates',[entry.get('certificate')])
    if not isinstance(names,list) or not 1<=len(names)<=4 or any(
            not isinstance(x,str) or not x for x in names) or len(set(names))!=len(names):
        raise ValueError('Configure one to four distinct issuer certificates')
    return names


def certificate_path(file,name):
    path=(file.parent/name).resolve()
    if not path.is_relative_to(file.parent.resolve()):
        raise ValueError('Issuer certificate must be inside the trust folder')
    return path


def certificate_fingerprint(pem):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    return x509.load_pem_x509_certificate(pem).fingerprint(hashes.SHA256()).hex()


def policy_fingerprint():
    path = os.environ.get('SKYCAM_ISSUER_TRUST')
    if not path:
        return None
    file = Path(path)
    try:
        raw = file.read_bytes()
        policy = read_policy(file)
        digest = hashlib.sha256(raw)
        for entry in policy.get('issuers', {}).values():
            for name in certificate_names(entry):
                digest.update(certificate_path(file,name).read_bytes())
        return digest.hexdigest()
    except (OSError, ValueError, KeyError, TypeError):
        return 'invalid-policy'


def verify_issuer(packet):
    config_path = os.environ.get('SKYCAM_ISSUER_TRUST')
    if not config_path:
        return {'status': 'not_configured', 'verified': False}
    from lxml import etree
    from signxml import XMLVerifier, SignatureConfiguration
    from .alert_verification import safe_xml
    safe_xml(packet)
    policy_path = Path(config_path)
    policy = read_policy(policy_path)
    root = etree.fromstring(packet, etree.XMLParser(resolve_entities=False, no_network=True))
    sender = root.findtext('{'+CAP+'}sender')
    entry = policy.get('issuers', {}).get(sender)
    if entry is None:
        if policy.get('require_all', False):
            raise ValueError('Issuer has no configured trust certificate')
        return {'status': 'sender_not_configured', 'verified': False}
    if entry.get('disabled',False):
        raise ValueError('Issuer is disabled by local trust policy')
    signature_tag = '{'+DS+'}Signature'
    wrappers = [s for s in root.findall(signature_tag) if s.get('Id') == 'NAADS Signature']
    # The wrapper has already passed DSS. Remove only that direct wrapper to
    # recover the issuer-signed document, without reserializing namespace state.
    for wrapper in wrappers:
        root.remove(wrapper)
    signatures = root.findall('.//'+signature_tag)
    if len(signatures) != 1 or signatures[0].getparent() is not root:
        raise ValueError('Exactly one direct issuer signature is required')
    signature = signatures[0]
    refs = signature.findall('{'+DS+'}SignedInfo/{'+DS+'}Reference')
    if len(refs) != 1 or refs[0].get('URI') != '':
        raise ValueError('Issuer signature must cover the complete CAP document')
    transforms = refs[0].findall('{'+DS+'}Transforms/{'+DS+'}Transform')
    allowed = {DS+'enveloped-signature', 'http://www.w3.org/2006/12/xml-c14n11',
               'http://www.w3.org/2001/10/xml-exc-c14n#',
               'http://www.w3.org/TR/2001/REC-xml-c14n-20010315'}
    if any(t.get('Algorithm') not in allowed for t in transforms):
        raise ValueError('Unsupported issuer signature transform')
    revoked={x.lower() for x in entry.get('revoked_sha256',[])}
    failures=[];result=None
    for name in certificate_names(entry):
        cert=certificate_path(policy_path,name).read_bytes()
        fingerprint=certificate_fingerprint(cert)
        if fingerprint in revoked:
            failures.append(ValueError('Issuer certificate has been locally revoked'))
            continue
        try:
            result=XMLVerifier().verify(root, x509_cert=cert,
                expect_config=SignatureConfiguration(location='./', expect_references=1))
            break
        except Exception as exc:
            failures.append(exc)
    if result is None:
        raise failures[-1]
    if result.signed_xml.tag != '{'+CAP+'}alert':
        raise ValueError('Issuer did not sign a complete CAP alert')
    # Only accept exactly the payload being parsed by the receiver. SignXML
    # strips unsigned comments, so compare ordinary element text/attributes.
    root.remove(signature)
    def shape(node):
        return (node.tag, sorted(node.attrib.items()), node.text or '',
                [(shape(c), c.tail or '') for c in node if isinstance(c.tag, str)])
    if shape(root) != shape(result.signed_xml):
        raise ValueError('Signed CAP payload differs from received payload')
    return {'status': 'verified', 'verified': True, 'sender': sender,
            'certificate_sha256': hashlib.sha256(cert).hexdigest(),
            'certificate_der_sha256': fingerprint,
            'method': 'Pinned issuer certificate, full-document XML signature'}
