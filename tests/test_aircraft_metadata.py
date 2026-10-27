import httpx
from skycam.aircraft_metadata import AircraftMetadata


def test_hierarchical_local_database_and_unknowns():
    db=AircraftMetadata('http://receiver/db/')
    def reply(request):
        if request.url.path=='/db/A.json':return httpx.Response(200,json={'children':['AB']})
        return httpx.Response(200,json={'7613':{'t':'B789','r':'N123AB'},'0000':{'t':'bad<script>'}})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        assert db.fetch('AB7613',client)=={'aircraft_type':'B789','registration':'N123AB','metadata_source':'LOCAL SKYAWARE DATABASE'}
        assert db.fetch('AB0000',client)=={}
        assert db.fetch('AB1111',client)=={}


def test_cache_expiry_queue_bounds_and_invalid_hex():
    db=AircraftMetadata();assert db.lookup('../secret')=={} and not db.pending
    for index in range(100):db.lookup(f'{index:06x}')
    assert len(db.pending)==64
    db.cache['AB7613']={'checked_at':100,'data':{'aircraft_type':'B789'}}
    assert db.lookup('ab7613',101)['aircraft_type']=='B789'
    assert db.lookup('ab7613',100+86401)=={} and 'AB7613' in db.pending
