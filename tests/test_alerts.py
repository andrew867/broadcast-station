from datetime import datetime,timezone
import pytest
from skycam.alerts import Alerts,Framer,HOSTS,repository_path

NOW=datetime(2026,10,17,16,tzinfo=timezone.utc).timestamp()
def message(identifier='one',kind='Alert',references='',status='Actual',immediate='no',expires='2026-10-17T18:00:00Z',code='1001519',sender='test-issuer'):
 return f'''<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>{identifier}</identifier><sender>{sender}</sender><sent>2026-10-17T15:00:00Z</sent><status>{status}</status><msgType>{kind}</msgType><scope>Public</scope><references>{references}</references><info><language>en-CA</language><category>Met</category><event>Fixture weather</event><headline>OFF-AIR TEST ONLY</headline><effective>2026-10-17T15:00:00Z</effective><expires>{expires}</expires><parameter><valueName>layer:SOREM:1.0:Broadcast_Immediately</valueName><value>{immediate}</value></parameter><area><areaDesc>Fixture area</areaDesc><geocode><valueName>profile:CAP-CP:Location:0.3</valueName><value>{code}</value></geocode></area></info></alert>'''.encode()

def test_stream_framing_fragmented_and_coalesced():
 packet=b'<?xml version="1.0"?>'+message();f=Framer()
 assert not f.feed(packet[:15]);assert f.feed(packet[15:]+packet)==[packet,packet]

def test_duplicate_expiry_test_and_immediate_filters(tmp_path):
 a=Alerts(tmp_path,verifier=lambda _: {'verified':True});a.ingest(message(),HOSTS[0],NOW);a.ingest(message(),HOSTS[1],NOW)
 assert len(a.public(NOW)['alerts'])==1
 for id,status,bi,code in [('test','Test','no','1001519'),('bi','Actual','yes','1001519'),('away','Actual','no','3500000')]:a.ingest(message(id,status=status,immediate=bi,code=code),HOSTS[0],NOW)
 assert len(a.public(NOW)['alerts'])==1 and len(a.public(NOW)['immediate'])==1
 assert a.public(NOW+3*3600)['alerts']==[]

def test_cancel_before_original_and_update_replaces(tmp_path):
 a=Alerts(tmp_path,verifier=lambda _: {'verified':True});ref='test-issuer,one,2026-10-17T15:00:00Z'
 a.ingest(message('cancel',kind='Cancel',references=ref),HOSTS[0],NOW)
 a.ingest(message(),HOSTS[0],NOW);assert not a.public(NOW)['alerts']
 a.ingest(message('two'),HOSTS[0],NOW)
 a.ingest(message('three',kind='Update',references=ref.replace('one','two')),HOSTS[0],NOW)
 assert [x['identifier'] for x in a.public(NOW)['alerts']]==['three']

def test_different_sender_cannot_cancel(tmp_path):
 a=Alerts(tmp_path,verifier=lambda _: {'verified':True});a.ingest(message(),HOSTS[0],NOW)
 a.ingest(message('cancel',kind='Cancel',references='test-issuer,one,2026-10-17T15:00:00Z',sender='other'),HOSTS[0],NOW)
 assert len(a.public(NOW)['alerts'])==1

def test_heartbeat_queues_recovery_and_freshness_expires(tmp_path):
 a=Alerts(tmp_path,verifier=lambda _: {'verified':True});a.feeds[HOSTS[0]]['connected']=True
 a.ingest(message('hb',status='System',sender='NAADS-Heartbeat',references='test-issuer,one,2026-10-17T15:00:00Z'),HOSTS[0],NOW)
 assert a.public(NOW)['fresh'] and len(a.pending)==1
 assert not a.public(NOW+151)['fresh']
 assert repository_path(('test-issuer','one','2026-10-17T15:00:00Z'))=='/2026-10-17/2026_10_17T15_00_00ZIone.xml'

def test_reject_entities_and_missing_expiry(tmp_path):
 a=Alerts(tmp_path,verifier=lambda _: {'verified':True})
 with pytest.raises(ValueError):a.ingest(b'<!DOCTYPE alert []>'+message(),HOSTS[0],NOW)
 a.ingest(message(expires=''),HOSTS[0],NOW);assert not a.public(NOW)['alerts']
