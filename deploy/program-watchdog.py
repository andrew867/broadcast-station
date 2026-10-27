#!/usr/bin/env python3
"""Independent, bounded recovery for a hung engine or controller.

Runs on the host, outside both containers. Reads AMCP directly; a stale web
status or a quiet/static camera never counts as proof of a frozen program.
"""
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path('/srv/station')
RUNTIME = Path(f'/run/user/{getattr(os, "getuid", lambda: 1000)()}/skycam-runtime')
HISTORY = ROOT/'data-web/broadcast/watchdog-history.json'

def recovery_history(value, now):
    """Keep usable recent events; malformed diagnostics must not disable recovery."""
    if not isinstance(value,list):return []
    rows={}
    for row in value[-1000:]:
        if not isinstance(row,dict):continue
        at=row.get('at')
        if (type(at) not in (int,float) or not math.isfinite(at)
                or not now-86400<=at<=now or row.get('target') not in ('engine','web')
                or not isinstance(row.get('reason'),str)):continue
        rows[(at,row['target'])]={'at':at,'target':row['target'],'reason':row['reason'][:300]}
    return sorted(rows.values(),key=lambda row:row['at'])


class Guard:
    def __init__(self, now, history=None):
        self.started = now
        self.identity = None
        self.last_frame = None
        self.changed = now
        self.bad_engine = None
        self.bad_web = None
        self.history = recovery_history(history,now)
        self.last_reason = 'Startup grace period'

    def observe(self, now, engine, web_running, frame, web_ok, maintenance=False, delivery_advancing=False):
        # Deliberately stopped/paused services must stay stopped/paused.
        if maintenance or not engine or not engine.get('Running') or engine.get('Paused'):
            self.started = self.changed = now
            self.bad_engine = self.bad_web = None
            self.last_reason = 'Maintenance or engine deliberately stopped/paused'
            return None
        identity = (engine.get('Pid'), engine.get('StartedAt'))
        if identity != self.identity:
            self.identity = identity
            self.started = self.changed = now
            self.last_frame = None
            self.bad_engine = self.bad_web = None
        if frame is not None and frame != self.last_frame:
            self.changed = now
            self.last_frame = frame
        if now-self.started < 90:
            self.last_reason = 'Startup grace period'
            return None
        self.bad_engine = (self.bad_engine if self.bad_engine is not None else now) if frame is None else None
        self.bad_web = (self.bad_web if self.bad_web is not None else now) if web_running and not web_ok else None
        target = None
        if delivery_advancing:
            self.bad_engine = None
            self.changed = now
            self.last_reason = 'Control degraded; independent program delivery is advancing'
            if self.bad_web is not None and now-self.bad_web >= 30:
                target = 'web'; self.last_reason = 'Controller unavailable; independent program delivery is advancing'
            else:
                return None
        elif self.bad_engine is not None and now-self.bad_engine >= 30:
            target = 'engine'; self.last_reason = 'AMCP output query unavailable for 30 seconds'
        elif frame is not None and now-self.changed >= 45:
            target = 'engine'; self.last_reason = 'Encoded output frame counter stalled for 45 seconds'
        elif frame is not None and self.bad_web is not None and now-self.bad_web >= 30:
            target = 'web'; self.last_reason = 'Controller unavailable or stale for 30 seconds'
        else:
            self.last_reason = 'Watching output and controller' if frame is not None and web_ok else 'Waiting for sustained failure'
        if not target:
            return None
        if self.history and now-self.history[-1]['at'] < 180:
            self.last_reason = 'Recovery cooldown; '+self.last_reason
            return None
        if len([h for h in self.history if now-h['at'] < 3600]) >= 3:
            self.last_reason = 'Recovery limit reached; operator attention required'
            return None
        return target

    def recovered(self, now, target, reason):
        self.history = [h for h in self.history if now-h['at'] < 86400]
        self.history.append({'at': now, 'target': target, 'reason': reason})
        self.started = self.changed = now
        self.bad_engine = self.bad_web = None

    def recovery_budget(self, now):
        recent = sorted(h['at'] for h in self.history if now-h['at'] < 3600)
        remaining = max(0, 3-len(recent))
        return {'remaining': remaining,
                'available_at': recent[-3]+3600 if not remaining else None}


def run(*args, timeout=8):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-300:])
    return result.stdout


def container(name):
    return json.loads(run('docker', 'inspect', '--format={{json .State}}', name))


def output_frame():
    with socket.create_connection(('127.0.0.1', 5250), timeout=3) as s:
        s.settimeout(3)
        s.sendall(b'INFO 1\r\n')
        data = b''
        while True:
            part = s.recv(65536)
            if not part or len(data) > 2_000_000:
                raise ValueError('Incomplete AMCP channel reply')
            data += part
            if b'<?xml' in data:
                try:
                    root = ET.fromstring(data[data.index(b'<?xml'):].strip())
                    break
                except ET.ParseError:
                    pass
    if not data.startswith(b'201 '):
        raise ValueError('AMCP query rejected')
    node = root.find('.//output/port/port_1/file/frame')
    return int(node.text) if node is not None else None


def controller_ok():
    with urllib.request.urlopen('http://127.0.0.1:8765/api/broadcast', timeout=4) as response:
        data = json.load(response)
    return 0 <= time.time()-data['playout'].get('checked_at', 0) < 60


class DeliveryProbe:
    """Fallback uses decoded frame timestamps, not merely an open socket."""
    def __init__(self):
        self.pts = None
        self.last_check = -100
        self.last_advance = -100
        self.error = None
    def observe(self, now, pts):
        if pts is not None:
            if self.pts is not None and pts > self.pts:
                self.last_advance = now
            self.pts = pts
        return now-self.last_advance < 20
    def check(self, now):
        if now-self.last_check >= 10:
            self.last_check = now
            try:
                raw = run('ffprobe','-v','error','-rw_timeout','4000000',
                    '-read_intervals','%+0.5','-select_streams','v:0',
                    '-show_frames','-show_entries','frame=best_effort_timestamp_time',
                    '-of','json','rtmp://192.0.2.10:1935/skycam-program',timeout=7)
                frames = json.loads(raw).get('frames',[])
                pts = [float(f['best_effort_timestamp_time']) for f in frames if 'best_effort_timestamp_time' in f]
                self.observe(now,max(pts) if pts else None)
                self.error = None
            except Exception as exc:
                self.error = str(exc)[:160]
        return now-self.last_advance < 20


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    tmp.replace(path)


def recover(target, web_running):
    # Bounded evidence, no relay URLs or stream keys. Keep only the latest event.
    for name in (['skycam-caspar', 'skycam-web'] if target == 'engine' else ['skycam-web']):
        try:
            log = subprocess.run(['docker', 'logs', '--tail', '35', name], capture_output=True, text=True, timeout=5)
            (RUNTIME/(name+'-recovery.log')).write_text((log.stdout+log.stderr)[-24000:], encoding='utf-8')
        except Exception:
            pass
    if target == 'engine':
        run('docker', 'restart', '-t', '5', 'skycam-caspar', timeout=35)
    if web_running:
        run('docker', 'restart', '-t', '5', 'skycam-web', timeout=35)


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    try:
        if HISTORY.stat().st_size>256_000:raise ValueError('Recovery history exceeds size limit')
        history = json.loads(HISTORY.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        history = []
    guard = Guard(time.time(), history)
    delivery = DeliveryProbe()
    while True:
        frame = None; error = None; engine = None; web_running = False; web_ok = False
        try:
            engine = container('skycam-caspar')
            web = container('skycam-web')
            web_running = bool(web.get('Running') and not web.get('Paused'))
            try: frame = output_frame()
            except Exception as exc: error = str(exc)[:200]
            if web_running:
                try: web_ok = controller_ok()
                except Exception as exc: error = str(exc)[:200]
            maintenance = (RUNTIME/'maintenance').exists()
            advancing = False
            if not maintenance and engine.get('Running') and not engine.get('Paused') and (frame is None or time.time()-guard.changed > 15):
                advancing = delivery.check(time.time())
            elif frame is not None and frame != guard.last_frame:
                # A recovered primary counter supersedes an old fallback error.
                delivery.error = None
            action = guard.observe(time.time(), engine, web_running, frame, web_ok, maintenance, advancing)
            if action:
                reason = guard.last_reason
                # Persist before attempting recovery, including failed attempts.
                guard.recovered(time.time(), action, reason)
                atomic_json(HISTORY, guard.history)
                print(f'Recovering {action}: {reason}', flush=True)
                recover(action, web_running)
        except Exception as exc:
            error = str(exc)[:200]
            guard.last_reason = 'Recovery or inspection error; '+error
        atomic_json(RUNTIME/'watchdog.json', {'checked_at': time.time(), 'note': guard.last_reason,
                    'frame': frame, 'error': error, 'history': guard.history[-3:],
                    'maintenance': (RUNTIME/'maintenance').exists(),
                    'delivery_last_advance': delivery.last_advance, 'delivery_probe_error': delivery.error,
                    'recovery_budget': guard.recovery_budget(time.time())})
        time.sleep(5)


if __name__ == '__main__':
    main()
