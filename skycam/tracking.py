from collections import defaultdict, deque
import math
import time
import numpy as np
from .geometry import ecef, enu_rotation


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class Tracks:
    def __init__(self):
        self.history = defaultdict(lambda: deque(maxlen=180))
        self.latest = None
        self.received = 0
        self.received_mono = 0
        self.error = 'Waiting for receiver'
        self.count = 0
        self.rejected = 0

    def ingest(self, data, now=None):
        now = time.time() if now is None else now
        stamp = data.get('now')
        if not number(stamp) or not -1 <= now-stamp <= 3:
            raise ValueError('Receiver snapshot clock is stale or ahead of host clock')
        if not isinstance(data.get('aircraft'), list):
            raise ValueError('Malformed receiver aircraft array')
        if self.latest is not None and stamp < self.latest:
            raise ValueError('Receiver clock moved backwards')
        self.latest, self.received, self.received_mono = stamp, now, time.monotonic()
        self.error, self.count, self.rejected = None, len(data['aircraft']), 0
        for a in data['aircraft']:
            if not isinstance(a, dict):
                self.rejected += 1
                continue
            required = ['lat','lon','alt_geom','seen_pos']
            if (not all(number(a.get(k)) for k in required) or not a.get('hex') or
                not -90 <= a['lat'] <= 90 or not -180 <= a['lon'] <= 180 or
                not -2000 < a['alt_geom'] < 100000 or not 0 <= a['seen_pos'] <= 5 or
                a.get('alt_baro') == 'ground' or a.get('mlat') or a.get('tisb')):
                self.rejected += 1
                continue
            t = stamp-a['seen_pos']
            h = str(a['hex'])[:16]
            q = self.history[h]
            if q and t <= q[-1]['time']+.03:
                continue
            pos = ecef(a['lat'], a['lon'], a['alt_geom']*.3048)
            velocity = None
            if (all(number(a.get(k)) for k in ['gs','track','geom_rate']) and
                0 <= a['gs'] <= 900 and abs(a['geom_rate']) <= 10000 and
                (not number(a.get('track_rate')) or abs(a['track_rate']) <= 3)):
                heading = math.radians(a['track'])
                speed = a['gs']*.514444
                velocity = enu_rotation(a['lat'], a['lon']).T @ np.array(
                    [speed*math.sin(heading),speed*math.cos(heading),a['geom_rate']*.3048/60])
            if q and t-q[-1]['time'] < 10 and np.linalg.norm(pos-q[-1]['pos'])/(t-q[-1]['time']) > 600:
                # A jump poisons both sides of interpolation; restart the track.
                q.clear()
                self.rejected += 1
                continue
            category=str(a.get('category','')).strip().upper()
            category_at=t
            if len(category)!=2 or category[0] not in 'AB' or category[1] not in '1234567':
                # Category is sent less often than position. Preserve only a
                # recent explicit report, never extend its age by copying it.
                prior=q[-1] if q else {}
                category_at=prior.get('category_at',-1e12)
                category=prior.get('category','') if 0<=t-category_at<=120 else ''
            q.append({'time':t,'pos':pos,'velocity':velocity,
                      'callsign':str(a.get('flight','')).strip()[:16] or h,
                      'category':category,'category_at':category_at,
                      'aircraft_type':str(a.get('t','')).strip()[:12],
                      'registration':str(a.get('r','')).strip()[:16],
                      'lat':a['lat'],'lon':a['lon'],'track':a.get('track',0) if number(a.get('track')) else 0,'hex':h,'altitude_ft':a['alt_geom'],'speed_kt':a.get('gs') if number(a.get('gs')) else None})
        for h in list(self.history):
            q = self.history[h]
            while q and q[0]['time'] < now-120:
                q.popleft()
            if not q:
                del self.history[h]

    def status(self, now=None):
        now = time.time() if now is None else now
        age = now-self.latest if self.latest is not None else None
        healthy = (self.error is None and age is not None and -1 <= age <= 3 and
                   time.monotonic()-self.received_mono <= 3)
        return {'healthy':healthy,'error':self.error,'snapshot_age_s':age,
                'receiver_time':self.latest,'aircraft_received':self.count,
                'rejected_latest':self.rejected,'buffered_tracks':len(self.history)}

    def positions(self, target, now=None):
        now = time.time() if now is None else now
        if not self.status(now)['healthy']:
            return []
        results = []
        for q in self.history.values():
            before = [p for p in q if p['time'] <= target]
            after = [p for p in q if p['time'] > target]
            if not before:
                continue  # Never back-project a new position into earlier video.
            a = before[-1]
            dt = target-a['time']
            mode, pos = 'held', a['pos']
            if after and after[0]['time']-a['time'] <= 3:
                b = after[0]
                pos = a['pos'] + (b['pos']-a['pos'])*dt/(b['time']-a['time'])
                mode = 'interpolated'
            elif dt <= .15:
                pass
            elif dt <= 2 and a['velocity'] is not None and now-a['time'] <= 5:
                pos = a['pos']+a['velocity']*dt
                mode = 'extrapolated'
            else:
                continue
            results.append({**a,'pos':pos,'mode':mode,'position_age_s':now-a['time']})
        return results
