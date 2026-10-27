import pytest
from tools.review_soak import review, bytes_value


def row(at, ready=True, generation=1):
    return {'at': at, 'fps': 30, 'moving': True,
            'decoded_sources': {'cam1': {'ready': ready, 'generation': generation}}}


def test_outage_groups_are_observations_not_invented_durations():
    data = [row(0), row(30, False), row(60, False), row(90, True, 2)]
    data[0]['unready_cameras'] = ['cam1']
    result = review(data)
    source = result['sources']['cam1']
    assert source['unready_samples'] == 2 and source['observed_unready_groups'] == 1
    assert source['episodes'] == [{'first_unready_at': 30, 'last_unready_at': 60,
        'samples': 2, 'recovered_at': 90, 'observed_span_seconds': 30}]
    assert source['generation_sequence'] == [1, 2]
    assert result['native_unready_samples_by_camera'] == {'cam1': 1}


def test_missing_probe_and_large_gap_do_not_claim_continuous_outage_or_recovery():
    data = [row(0, False), {'at': 30, 'source_probe_unavailable': True},
            row(60), row(90, False), row(300), row(330, False)]
    result = review(data)
    assert len(result['observation_gaps']) == 1
    episodes = result['sources']['cam1']['episodes']
    assert len(episodes) == 3 and all(e['recovered_at'] is None for e in episodes)
    assert result['sources']['cam1']['unknown_samples'] == 1


def test_service_replacement_and_old_watchdog_events_are_distinguished():
    data = [row(100), row(130)]
    for i, r in enumerate(data):
        r['services'] = {'engine': {'started': str(i), 'restarts': 0, 'running': True, 'oom': False}}
        r['watchdog'] = {'history': [{'at': 10, 'target': 'web'}, {'at': 110, 'target': 'engine'}]}
    result = review(data)
    assert result['services']['engine']['starts'] == ['0', '1']
    assert len(result['watchdog_events_during_observation']) == 1


def test_resource_units_and_counter_resets_are_explicit():
    data = [row(0), row(30), row(60)]
    for r, written in zip(data, ['2GB', '3GB', '1MB']):
        r['resources'] = [{'Name': 'studio', 'MemUsage': '1GiB / 2GiB',
                          'BlockIO': '0B / '+written, 'CPUPerc': '120%', 'PIDs': '40'}]
    result = review(data)['resources']['studio']
    assert result['memory']['max'] == 1024**3
    assert result['write_counter_resets'] == 1
    assert result['observed_write_increase_bytes'] == 1000**3
    assert bytes_value('bad') is None


def test_empty_and_invalid_timeline():
    assert review([])['fps']['mean'] is None
    for data in [[row(1), row(1)], [row(float('nan'))], [row(2), row(1)]]:
        with pytest.raises(ValueError): review(data)
