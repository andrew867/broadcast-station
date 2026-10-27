"""Optional, manually requested AeroAPI details with conservative spending limits.

No polling, map image purchases, pagination, automatic retries or on-air changes.
Prices verified against FlightAware Personal pricing on 2026-10-20.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
import json
import re
import sqlite3
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://aeroapi.flightaware.com/aeroapi/'
DETAIL_MICRO_USD = 5000
CAP_MICRO_USD = 8_000_000
PRICING_VERIFIED = '2026-10-20'


class Unavailable(RuntimeError):
    pass


def money(value):
    try:
        value = Decimal(str(value))
        if not value.is_finite() or value < 0:
            raise ValueError()
        return int((value * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
    except Exception:
        raise Unavailable('Usage cost is missing or invalid') from None


class AeroAPI:
    def __init__(self, folder, key_file, transport=None, clock=time.time):
        self.folder = Path(folder)
        self.key_file = Path(key_file)
        self.clock = clock
        self.transport = transport or self._request
        self.folder.mkdir(parents=True, exist_ok=True)
        self.policy = self.folder / 'policy.json'
        self.ledger = self.folder / 'usage.sqlite'
        # A missing ledger with an existing policy is a recovery problem,
        # never an excuse to silently reset the spending counter.
        if self.policy.exists() and not self.ledger.exists():
            raise Unavailable('Usage ledger missing; restore it before proceeding')
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS charges (at REAL, period TEXT, ident TEXT, micro_usd INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS cache (ident TEXT PRIMARY KEY, at REAL, body TEXT)')
        if not self.policy.exists():
            with self.policy.open('x', encoding='utf-8') as out:
                json.dump({'enabled': False, 'period': self.period(),
                           'confirmed_credit_usd': 0, 'pricing_verified': PRICING_VERIFIED}, out, indent=2)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.ledger, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def period(self):
        return datetime.fromtimestamp(self.clock(), timezone.utc).strftime('%Y-%m')

    def _request(self, path, params):
        try:
            key = self.key_file.read_text().strip()
            if not key or any(c.isspace() for c in key):
                raise Unavailable('AeroAPI key is missing or invalid')
            request = urllib.request.Request(BASE + path + '?' + urllib.parse.urlencode(params),
                                             headers={'x-apikey': key, 'Accept': 'application/json'})
            # Do not send the private header to a redirected destination.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
                payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise Unavailable('AeroAPI response exceeded the size limit')
            return json.loads(payload)
        except urllib.error.HTTPError as exc:
            raise Unavailable(f'AeroAPI returned HTTP {exc.code}; no retry sent') from None
        except (OSError, ValueError):
            raise Unavailable('AeroAPI request failed; no retry sent') from None

    def usage(self):
        # A rolling 35-day window includes the whole current billing month
        # regardless of a small boundary/timezone difference. This can stop
        # requests early, deliberately.
        start = datetime.fromtimestamp(self.clock(), timezone.utc) - timedelta(days=35)
        data = self.transport('account/usage', {'start': start.strftime('%Y-%m-%d'), 'all_keys': 'true'})
        if not isinstance(data, dict):
            raise Unavailable('Unrecognized usage response')
        cost = money(data.get('total_cost'))
        return {'provider_micro_usd': cost, 'provider_window_days': 35,
                'checked_at': self.clock(), 'scope': 'all account keys'}

    def status(self, refresh=False):
        policy = json.loads(self.policy.read_text())
        with self._db() as db:
            local = db.execute('SELECT COALESCE(SUM(micro_usd),0) FROM charges WHERE period=?',
                               (self.period(),)).fetchone()[0]
        return {'enabled': bool(policy.get('enabled')), 'period': self.period(),
                'armed_period': policy.get('period'), 'local_reserved_usd': local / 1_000_000,
                'cap_usd': 8, 'key_present': self.key_file.is_file(),
                'price_per_detail_page_usd': .005,
                'usage': self.usage() if refresh else None}

    def lookup(self, ident):
        ident = ident.strip().upper()
        if not re.fullmatch(r'[A-Z0-9-]{2,12}', ident):
            raise Unavailable('Use a flight callsign or registration')
        now = self.clock()
        # Serialize lookups across processes. Cache hits never spend money.
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            cached = db.execute('SELECT at,body FROM cache WHERE ident=?', (ident,)).fetchone()
            if cached and 0 <= now-cached[0] < 86400:
                return {'cached': True, 'fetched_at': cached[0], 'data': json.loads(cached[1])}
            policy = json.loads(self.policy.read_text())
            if not policy.get('enabled') or policy.get('period') != self.period():
                raise Unavailable('Paid lookups are disabled or require a new month review')
            if money(policy.get('confirmed_credit_usd')) < 10_000_000:
                raise Unavailable('The feeder allowance has not been confirmed')
            try:
                reviewed = datetime.fromisoformat(policy['pricing_verified']).replace(tzinfo=timezone.utc).timestamp()
            except (KeyError, TypeError, ValueError):
                raise Unavailable('Pricing review is required') from None
            if not 0 <= now-reviewed <= 31*86400:
                raise Unavailable('Pricing review is required')
            usage = self.usage()
            local = db.execute('SELECT COALESCE(SUM(micro_usd),0) FROM charges WHERE period=?',
                               (self.period(),)).fetchone()[0]
            # Intentionally double-count known local calls against provider
            # cost. Never subtract an uncertain delayed report.
            if usage['provider_micro_usd'] + local + DETAIL_MICRO_USD > CAP_MICRO_USD:
                raise Unavailable('Conservative US$8 budget reached')
            recent = db.execute('SELECT COUNT(*) FROM charges WHERE at>?', (now-60,)).fetchone()[0]
            daily = db.execute('SELECT COUNT(*) FROM charges WHERE at>?', (now-86400,)).fetchone()[0]
            if recent >= 2 or daily >= 20:
                raise Unavailable('Lookup rate limit reached')
            db.execute('INSERT INTO charges VALUES (?,?,?,?)', (now,self.period(),ident,DETAIL_MICRO_USD))
            db.commit()  # Reservation survives a timeout, crash or rejected call.
        today = datetime.fromtimestamp(now, timezone.utc)
        data = self.transport('flights/'+urllib.parse.quote(ident, safe=''), {
            'max_pages': 1,
            'start': (today-timedelta(days=1)).strftime('%Y-%m-%d'),
            'end': (today+timedelta(days=1)).strftime('%Y-%m-%d')})
        if not isinstance(data, dict) or not isinstance(data.get('flights'), list):
            raise Unavailable('Invalid flight response; reservation retained')
        # Return candidates without guessing which repeated daily callsign is
        # the aircraft currently shown by the local receiver.
        body = json.dumps(data)
        with self._db() as db:
            db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (ident,now,body))
        return {'cached': False, 'fetched_at': now, 'data': data}


def main():
    parser = argparse.ArgumentParser(description='Optional FlightAware backup flight details')
    parser.add_argument('--folder', type=Path, default=Path.home()/'.local/state/skycam-aeroapi')
    parser.add_argument('--key-file', type=Path, default=Path.home()/'.config/skycam/flightaware.key')
    parser.add_argument('--usage', action='store_true', help='Read free account-wide usage report')
    parser.add_argument('--lookup', help='Manual cached flight lookup; disabled by default')
    args = parser.parse_args()
    try:
        client = AeroAPI(args.folder,args.key_file)
        result = client.lookup(args.lookup) if args.lookup else client.status(args.usage)
        print(json.dumps(result,indent=2))
    except (Unavailable, OSError, ValueError, sqlite3.Error) as exc:
        # Never include request headers or key contents in diagnostics.
        print(json.dumps({'error': str(exc)}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
