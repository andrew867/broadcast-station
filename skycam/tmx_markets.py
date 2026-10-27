"""Small, optional TMX Money TSX adapter. Receipt time is never quote time."""
import asyncio
import copy
import json
import math
import threading
import time
from datetime import date, datetime, timezone

import httpx

ENDPOINT = 'https://app-money.tmx.com/graphql'
SOURCE_URL = 'https://money.tmx.com/en/quote/%5ETSX'
POLL_SECONDS = 120
MAX_RECEIPT_AGE = 600
MAX_BYTES = 128_000
QUOTE = {'operationName': 'getQuoteBySymbol', 'variables': {'symbol': '^TSX', 'locale': 'en'},
         'query': 'query getQuoteBySymbol($symbol: String, $locale: String) { getQuoteBySymbol(symbol: $symbol, locale: $locale) { symbol name price priceChange percentChange prevClose datatype currency } }'}
HISTORY = {'operationName': 'getIndexPriceHistory', 'variables': {'symbol': '^TSX', 'limit': 5},
           'query': 'query getIndexPriceHistory($symbol: String!, $limit: Int) { getIndexPriceHistory(symbol: $symbol, limit: $limit) { datetime closePrice } }'}


def number(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('TMX numeric field missing or invalid')
    if not math.isfinite(value) or (positive and not 0 < value < 1_000_000):
        raise ValueError('TMX numeric field outside valid range')
    return float(value)


def parse_quote(payload):
    if not isinstance(payload, dict) or payload.get('errors'):
        raise ValueError('TMX GraphQL quote error')
    row = payload.get('data', {}).get('getQuoteBySymbol')
    if not isinstance(row, dict) or row.get('symbol') != '^TSX' or row.get('datatype') != 'index':
        raise ValueError('TMX did not return the TSX index')
    value = number(row.get('price'), True)
    previous = number(row.get('prevClose'), True)
    delta = number(row.get('priceChange'))
    percent = number(row.get('percentChange'))
    if abs(value - previous - delta) > .03 or abs(delta / previous * 100 - percent) > .01:
        raise ValueError('TMX previous-close comparison is inconsistent')
    return {'value': value, 'change': delta, 'change_percent': percent, 'previous_close': previous}


def parse_history(payload, now):
    if not isinstance(payload, dict) or payload.get('errors'):
        raise ValueError('TMX GraphQL history error')
    rows = payload.get('data', {}).get('getIndexPriceHistory')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
        raise ValueError('TMX history must contain one to five daily bars')
    result = {}
    today = datetime.fromtimestamp(now, timezone.utc).date()
    for row in rows:
        day = date.fromisoformat(row['datetime'])
        if day > today or (today - day).days > 40:
            raise ValueError('TMX history date outside accepted window')
        # Midnight UTC is a chart coordinate for the daily bar, not a trade time.
        result[day.isoformat()] = {'date': day.isoformat(),
            'at': datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp(),
            'value': number(row.get('closePrice'), True)}
    return sorted(result.values(), key=lambda r: r['date'])


async def request(client, operation):
    async with client.stream('POST', ENDPOINT, json=operation) as response:
        response.raise_for_status()
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ValueError('TMX response exceeds size limit')
        return json.loads(body)


class TmxMarkets:
    def __init__(self, data, enabled=None):
        if enabled is None:
            try:
                config = json.loads((data / 'broadcast' / 'tmx-config.json').read_text())
                enabled = config.get('enabled') is True and config.get('redistribution_confirmed') is True
            except (OSError, ValueError, AttributeError):
                enabled = False
        self.enabled = bool(enabled)
        self.lock = threading.RLock()
        self.quote = None
        self.history = []
        self.received_at = self.history_received_at = 0
        self.errors = {}

    async def refresh(self, client=None, now=None):
        if not self.enabled:
            return
        if client is None:
            async with httpx.AsyncClient(timeout=15, trust_env=False, headers={
                    'locale': 'en', 'Referer': 'https://money.tmx.com/'}) as owned:
                return await self.refresh(owned, now)
        now = time.time() if now is None else now
        for key, operation in [('quote', QUOTE), ('history', HISTORY)]:
            if key == 'history' and self.history_received_at and now - self.history_received_at < 1800:
                continue
            try:
                payload = await request(client, operation)
                parsed = parse_quote(payload) if key == 'quote' else parse_history(payload, now)
                with self.lock:
                    if key == 'quote':
                        self.quote, self.received_at = parsed, now
                    else:
                        self.history, self.history_received_at = parsed, now
                    self.errors.pop(key, None)
            except Exception as exc:
                with self.lock:
                    self.errors[key] = type(exc).__name__ + ': TMX ' + key + ' refresh failed'

    def public(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            age = now - self.received_at
            available = self.enabled and self.quote is not None and 0 <= age < MAX_RECEIPT_AGE
            history = copy.deepcopy(self.history) if available and 0 <= now - self.history_received_at < 3600 else []
            return {'id': 'tsx', 'symbol': '^TSX', 'label': 'S&P/TSX COMPOSITE',
                'source': 'TMX MONEY', 'url': SOURCE_URL, 'enabled': self.enabled,
                'available': available, 'unit': 'INDEX POINTS', 'daily_reference': False,
                'quote_kind': 'INDEX QUOTE / DELAY UNVERIFIED', 'observed_at': None,
                'quote_time_known': False, 'delay_seconds': None, 'session': 'UNVERIFIED',
                'received_at': self.received_at or None, 'receipt_age_seconds': max(0, age) if self.received_at else None,
                'cached': bool(self.errors.get('quote')) or age >= POLL_SECONDS * 2,
                'history': history, 'history_kind': 'DAILY BARS / LATEST MAY BE IN PROGRESS',
                'history_received_at': self.history_received_at or None,
                'change_basis': 'PREVIOUS CLOSE (TMX)', 'errors': dict(self.errors),
                **(copy.deepcopy(self.quote) if available else {'value': None, 'change': None, 'change_percent': None, 'previous_close': None})}

    async def watch(self):
        if not self.enabled:
            return
        failures = 0
        while True:
            await self.refresh()
            failures = min(failures + 1, 4) if self.errors.get('quote') else 0
            await asyncio.sleep(min(1800, POLL_SECONDS * 2 ** failures))
