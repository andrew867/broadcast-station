# SPDX-License-Identifier: Apache-2.0
"""Review saved observations without contacting or decoding a running station."""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def bytes_value(value):
    match = re.fullmatch(r'([\d.]+)\s*(B|kB|MB|GB|TB|KiB|MiB|GiB|TiB)', str(value).strip())
    if not match:
        return None
    units = {'B': 1, 'kB': 1000, 'MB': 1000**2, 'GB': 1000**3, 'TB': 1000**4,
             'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
    return round(float(match[1]) * units[match[2]])


def source_review(rows, name, max_gap):
    episodes, active, previous = [], None, None
    generations, unknown, unready, ready = [], 0, 0, 0
    def finish(recovered=None):
        nonlocal active
        if active is not None:
            active['recovered_at'] = recovered
            active['observed_span_seconds'] = active['last_unready_at'] - active['first_unready_at']
            episodes.append(active)
            active = None
    for row in rows:
        at = row['at']
        source = row.get('decoded_sources', {}).get(name)
        if previous is not None and at - previous > max_gap:
            finish()
        previous = at
        if row.get('source_probe_unavailable') or not isinstance(source, dict) or type(source.get('ready')) is not bool:
            unknown += 1
            finish()
            continue
        generation = source.get('generation')
        if type(generation) is int and (not generations or generations[-1] != generation):
            generations.append(generation)
        if source['ready']:
            ready += 1
            finish(at)
        else:
            unready += 1
            if active is None:
                active = {'first_unready_at': at, 'last_unready_at': at, 'samples': 0}
            active['last_unready_at'] = at
            active['samples'] += 1
    finish()
    return {'ready_samples': ready, 'unready_samples': unready, 'unknown_samples': unknown,
            'generation_sequence': generations, 'observed_unready_groups': len(episodes), 'episodes': episodes}


def review(rows, max_gap=60):
    if not number(max_gap) or max_gap <= 0:
        raise ValueError('Observation gap limit must be positive')
    if any(not isinstance(r, dict) or not number(r.get('at')) for r in rows):
        raise ValueError('Each observation needs a finite numeric timestamp')
    if any(b['at'] <= a['at'] for a, b in zip(rows, rows[1:])):
        raise ValueError('Observation timestamps must increase strictly')
    rates = [r['fps'] for r in rows if number(r.get('fps'))]
    names = sorted({k for r in rows for k in r.get('decoded_sources', {})})
    services, resources, events = {}, {}, {}
    for row in rows:
        for name, state in row.get('services', {}).items():
            item = services.setdefault(name, {'observations': 0, 'starts': [], 'restart_count_max': 0,
                                              'not_running_samples': 0, 'oom_samples': 0})
            item['observations'] += 1
            if state.get('started') and state['started'] not in item['starts']:
                item['starts'].append(state['started'])
            item['restart_count_max'] = max(item['restart_count_max'], state.get('restarts', 0))
            item['not_running_samples'] += state.get('running') is False
            item['oom_samples'] += state.get('oom') is True
        for value in row.get('resources', []):
            # Docker names stay local to the report, no addresses or raw logs.
            item = resources.setdefault(value['Name'], {'memory': [], 'cpu': [], 'writes': [], 'pids': []})
            mem = bytes_value(str(value.get('MemUsage', '')).split('/')[0])
            if mem is not None:
                item['memory'].append(mem)
            parts = str(value.get('BlockIO', '')).split('/')
            write = bytes_value(parts[1]) if len(parts) == 2 else None
            if write is not None:
                item['writes'].append(write)
            for source, dest in [('CPUPerc', 'cpu'), ('PIDs', 'pids')]:
                try:
                    val = float(str(value.get(source, '')).rstrip('%'))
                    if math.isfinite(val): item[dest].append(val)
                except ValueError:
                    pass
        for event in row.get('watchdog', {}).get('history', []) or []:
            if isinstance(event, dict) and number(event.get('at')):
                # Exclude recovery events retained from before this observation.
                if rows[0]['at'] <= event['at'] <= rows[-1]['at']:
                    safe = {k: event.get(k) for k in ('at', 'target', 'reason')}
                    events[json.dumps(safe, sort_keys=True)] = safe
    resource_summary = {}
    for name, values in resources.items():
        out = {}
        for metric, samples in values.items():
            if samples:
                out[metric] = {'first': samples[0], 'last': samples[-1], 'min': min(samples), 'max': max(samples)}
        writes = values['writes']
        out['write_counter_resets'] = sum(b < a for a, b in zip(writes, writes[1:]))
        out['observed_write_increase_bytes'] = sum(max(0, b-a) for a, b in zip(writes, writes[1:]))
        resource_summary[name] = out
    gaps = [{'from': a['at'], 'to': b['at'], 'seconds': b['at']-a['at']}
            for a, b in zip(rows, rows[1:]) if b['at']-a['at'] > max_gap]
    return {'samples': len(rows), 'started_at': rows[0]['at'] if rows else None,
            'finished_at': rows[-1]['at'] if rows else None,
            'observed_seconds': rows[-1]['at']-rows[0]['at'] if rows else 0,
            'fps': {'min': min(rates, default=None), 'max': max(rates, default=None),
                    'mean': sum(rates)/len(rates) if rates else None},
            'program_probe_failures': sum(bool(r.get('error')) for r in rows),
            'program_not_moving_samples': sum(r.get('moving') is False for r in rows),
            'observation_gaps': gaps, 'sources': {n: source_review(rows, n, max_gap) for n in names},
            'native_unready_samples_by_camera': dict(Counter(k for r in rows for k in r.get('unready_cameras', []))),
            'services': services, 'resources': resource_summary,
            'watchdog_events_during_observation': sorted(events.values(), key=lambda e: e['at']),
            'scope': 'Sampled observations, not continuous outage durations. Groups split at missing probes or long observation gaps. No automatic acceptance verdict. Resource figures are Docker counters, not a disk-write attribution or leak proof.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples', type=Path)
    parser.add_argument('--max-gap', type=float, default=60)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.samples.read_text(encoding='utf-8').splitlines() if line.strip()]
    result = json.dumps(review(rows, args.max_gap), indent=2)
    if args.output:
        args.output.write_text(result+'\n', encoding='utf-8')
    else:
        print(result)


if __name__ == '__main__':
    main()
