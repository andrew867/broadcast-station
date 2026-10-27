from skycam.network_health import parse_ping,queue_totals

def test_missing_ping_is_unavailable_and_submillisecond_probe_parses():
    assert parse_ping('100% packet loss') is None
    assert parse_ping('64 bytes: time=124.55 ms')==124.55
    assert parse_ping('64 bytes: time<1 ms')==1

def test_queues_ignore_headers_and_sum_both_directions():
    assert queue_totals(None)['remote_connections'] is None
    assert queue_totals('')['remote_connections']==0
    text='State Recv-Q Send-Q Local Peer\nESTAB 0 450 a b\nESTAB 230 0 a b\n'
    assert queue_totals(text)=={'remote_connections':2,'receive_queue_bytes':230,'send_queue_bytes':450}
