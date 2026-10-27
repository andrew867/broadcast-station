"""Authenticate complete CAP documents using Pelmorex's HTTPS DSS service.

No URL or trust anchor supplied inside an alert is trusted. TLS certificate and
hostname validation are mandatory. Request IDs bind responses to exact requests.
"""
from .public_errors import public_error
import hashlib,re,time,uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import httpx

DS='http://www.w3.org/2000/09/xmldsig#'
DSS='http://www.docs.oasis-open.org/dss/oasis-dss-1.0-core-schema-cd-02.xsd'
SOAP='http://www.w3.org/2003/05/soap-envelope'
SERVICE='https://dss1.naad-adna.pelmorex.com/'
ENDPOINTS=tuple('https://'+h+'.naad-adna.pelmorex.com/PTINAADSDSSWebService.asmx' for h in ('dss1','dss2'))
SUCCESS='urn:oasis:names:tc:dss:1.0:resultmajor:Success'

def safe_xml(raw):
    if b'\x00' in raw:raise ValueError('Expected UTF-8 XML')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('DTD/entities prohibited')
    return ET.fromstring(raw)

def request_body(packet,request_id):
    root=safe_xml(packet)
    if root.tag!='{urn:oasis:names:tc:emergency:cap:1.2}alert':raise ValueError('Expected one CAP root')
    signatures=[s for s in root.findall('{'+DS+'}Signature') if s.get('Id')=='NAADS Signature']
    if len(signatures)!=1:raise ValueError('Exactly one direct NAADS signature required')
    references=signatures[0].findall('{'+DS+'}SignedInfo/{'+DS+'}Reference')
    if len(references)!=1 or references[0].get('URI')!='':raise ValueError('Signature must cover the complete alert')
    # Preserve signed XML bytes, including namespace declarations and whitespace.
    document=re.sub(r'^\s*<\?xml[^?]*\?>','',packet.decode('utf-8-sig'),count=1)
    verify=f'''<VerifyRequest RequestID="{request_id}" xmlns:ds="{DS}" xmlns="{DSS}" Profile="SkyCam247"><InputDocuments><Document ID="alert">{document}</Document></InputDocuments><OptionalInputs><SignaturePlacement WhichDocument="alert" CreateEnvelopedSignature="true"/></OptionalInputs><SignatureObject><SignaturePtr WhichDocument="alert" XPath="//cs:Signature[Id = &quot;NAADS Signature&quot;]"/></SignatureObject></VerifyRequest>'''
    return f'''<soap:Envelope xmlns:soap="{SOAP}" xmlns:svc="{SERVICE}"><soap:Body><svc:DSSVerifySignedNaadsAlert><svc:DSSMessageWithSignedAlertStr>{escape(verify)}</svc:DSSMessageWithSignedAlertStr></svc:DSSVerifySignedNaadsAlert></soap:Body></soap:Envelope>'''.encode()

def parse_response(content,request_id):
    root=safe_xml(content)
    results=root.findall('./{'+SOAP+'}Body/{'+SERVICE+'}DSSVerifySignedNaadsAlertResponse/{'+SERVICE+'}DSSVerifySignedNaadsAlertResult')
    if len(results)!=1 or not results[0].text:raise ValueError('Invalid DSS SOAP response')
    response=safe_xml(results[0].text.encode())
    if response.tag!='{'+DSS+'}VerifyResponse' or response.get('RequestID')!=request_id:raise ValueError('DSS response identity mismatch')
    major=response.findall('./{'+DSS+'}Result/{'+DSS+'}ResultMajor')
    if len(major)!=1 or major[0].text!=SUCCESS:raise ValueError('NAADS signature rejected by DSS')

class DssVerifier:
    def __call__(self,packet):
        request_id=str(uuid.uuid4());body=request_body(packet,request_id);errors=[]
        with httpx.Client(timeout=10,follow_redirects=False,trust_env=False) as client:
            for endpoint in ENDPOINTS:
                try:
                    with client.stream('POST',endpoint,content=body,headers={'Content-Type':'application/soap+xml; charset=utf-8'}) as response:
                        response.raise_for_status();content=bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content)>256*1024:raise ValueError('DSS response exceeds limit')
                    parse_response(bytes(content),request_id)
                    from .issuer_trust import verify_issuer
                    issuer=verify_issuer(packet)
                    return {'verified':True,'method':'NAADS DSS over verified HTTPS','endpoint':endpoint,'checked_at':time.time(),'sha256':hashlib.sha256(packet).hexdigest(),'issuer':issuer}
                except (httpx.HTTPError,ValueError,ET.ParseError) as exc:errors.append(public_error(exc)[:160])
        raise ValueError('Signature verification unavailable or rejected: '+'; '.join(errors))
