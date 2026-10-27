from .station_config import secret
"""Bounded Finnhub/OANDA quote receiver; connection health never proves freshness."""
import asyncio,json,math,os,threading,time
from collections import deque
from urllib.parse import quote
from .storage import save_json

SYMBOLS={'OANDA:USD_CAD':('fx','CAD / USD','USD FOR 1 CAD'),
         'OANDA:WTICO_USD':('wti','WTI / OANDA CFD','USD / OANDA OIL CFD'),
         'OANDA:BCO_USD':('brent','BRENT / OANDA CFD','USD / OANDA OIL CFD')}
SYMBOLS.update({
    'OANDA:XAU_USD':('gold','GOLD','USD / OANDA METAL CFD'),
    'OANDA:XAG_USD':('silver','SILVER','USD / OANDA METAL CFD'),
    'OANDA:XPT_USD':('platinum','PLATINUM','USD / OANDA METAL CFD'),
    'OANDA:XPD_USD':('palladium','PALLADIUM','USD / OANDA METAL CFD'),
    'AAPL':('aapl','APPLE / AAPL','USD PER SHARE'),
    'MSFT':('msft','MICROSOFT / MSFT','USD PER SHARE'),
    'NVDA':('nvda','NVIDIA / NVDA','USD PER SHARE'),
    'GOOGL':('googl','ALPHABET / GOOGL','USD PER SHARE'),
})
METALS=('gold','silver','platinum','palladium')
STOCKS=('aapl','msft','nvda','googl')
MAX_AGE=120
STOCK_MAX_AGE=30*60
STOCK_RETAIN_AGE=7*86400

class LiveMarkets:
    def __init__(self,key=None,cache_path=None):
        self.key=(secret('finnhub') or os.environ.get('FINNHUB_API_KEY','')) if key is None else key
        self.lock=threading.RLock();self.rows={};self.histories={};self.connected=False;self.error=None
        self.cache_path=None;self.last_saved=0
        if cache_path and cache_path.exists():
            try:
                cached=json.loads(cache_path.read_text(encoding='utf-8'))
                self.ingest({'type':'trade','data':[r for r in cached if isinstance(r,dict) and r.get('s') in SYMBOLS and SYMBOLS[r['s']][0] in STOCKS]})
            except (OSError,ValueError,TypeError):pass
        self.cache_path=cache_path

    def ingest(self,message,now=None):
        now=time.time() if now is None else now
        if not isinstance(message,dict) or message.get('type')!='trade':return
        rows=message.get('data',[])
        if not isinstance(rows,list):return
        with self.lock:
            for row in rows[:500]:
                if not isinstance(row,dict) or row.get('s') not in SYMBOLS:continue
                try:
                    price=float(row['p']);at=float(row['t'])/1000
                    retain=STOCK_RETAIN_AGE if SYMBOLS[row['s']][0] in STOCKS else 86400
                    if not math.isfinite(price) or not math.isfinite(at) or price<=0 or at>now+5 or at<now-retain:continue
                    symbol=row['s'];key,label,unit=SYMBOLS[symbol]
                    if key=='fx' and not .01<price<100:continue
                    if key!='fx' and price>10000:continue
                    previous=self.rows.get(key)
                    if previous and at<=previous['observed_at']:continue
                    value=1/price if key=='fx' else price
                    history=self.histories.setdefault(key,deque(maxlen=121))
                    continuous=previous and 0<at-previous['observed_at']<=MAX_AGE
                    if not continuous:history.clear()
                    while history and at-history[0]['at']>600:history.popleft()
                    point={'at':at,'value':value}
                    if history and int(history[-1]['at']//5)==int(at//5):history[-1]=point
                    else:history.append(point)
                    change=value-previous['value'] if continuous else None
                    self.rows[key]={'id':key,'label':label,'unit':unit,'value':value,
                        'observed_at':at,'received_at':now,'symbol':symbol,'source':'FINNHUB' if key in STOCKS else 'FINNHUB / OANDA',
                        'quote_kind':'STOCK PROVIDER UPDATE' if key in STOCKS else 'FX PROVIDER UPDATE' if key=='fx' else 'CFD PROVIDER UPDATE',
                        'change':change,'previous_value':previous['value'] if continuous else None,
                        'change_basis':'PREVIOUS PROVIDER UPDATE','url':'https://finnhub.io/docs/api/websocket-trades'}
                except (ValueError,TypeError,KeyError,OverflowError):continue
            if self.cache_path and time.monotonic()-self.last_saved>=60:
                self.last_saved=time.monotonic()
                try:
                    save_json(self.cache_path,[{'s':r['symbol'],'p':r['value'],'t':r['observed_at']*1000} for k,r in self.rows.items() if k in STOCKS])
                    self.last_saved=time.monotonic()
                except OSError:pass

    def public(self,now=None):
        now=time.time() if now is None else now
        with self.lock:
            rows={}
            for key,row in self.rows.items():
                age=now-row['observed_at']
                limit=STOCK_MAX_AGE if key in STOCKS else MAX_AGE
                fresh=-5<=age<=limit
                history=[dict(p) for p in self.histories.get(key,[]) if 0<=now-p['at']<=600]
                start=history[0] if len(history)>1 else None
                change=row['value']-start['value'] if start else None
                rows[key]={**row,'age_seconds':round(max(0,now-row['observed_at']),1),
                    'available':-5<=age<=(STOCK_RETAIN_AGE if key in STOCKS else limit),
                    'fresh':fresh,'max_age_seconds':limit,
                    'quote_status':'recent' if fresh else 'last_quote' if key in STOCKS and -5<=age<=STOCK_RETAIN_AGE else 'unavailable',
                    'cached':not self.connected or not fresh,
                    'history':history,'history_kind':'RECENT PROVIDER UPDATES',
                    'window_start_at':start['at'] if start else None,'window_change':change,
                    'window_percent':change/abs(start['value'])*100 if start and start['value'] else None,
                    'change_percent':row['change']/abs(row['previous_value'])*100 if row.get('previous_value') else None}
            return {'configured':bool(self.key),'connected':self.connected,'error':self.error,
                    'max_age_seconds':MAX_AGE,'stock_max_age_seconds':STOCK_MAX_AGE,
                    'stock_retain_age_seconds':STOCK_RETAIN_AGE,'quotes':rows}

    async def watch(self):
        if not self.key:return
        import websockets
        delay=2
        while True:
            try:
                async with websockets.connect('wss://ws.finnhub.io?token='+quote(self.key,safe=''),
                        open_timeout=15,close_timeout=3,ping_interval=20,ping_timeout=20,
                        max_size=262144,max_queue=4,proxy=None) as ws:
                    with self.lock:self.connected=True;self.error=None
                    for symbol in SYMBOLS:
                        await ws.send(json.dumps({'type':'subscribe','symbol':symbol}));await asyncio.sleep(.25)
                    while True:
                        raw=await asyncio.wait_for(ws.recv(),60)
                        message=json.loads(raw)
                        if isinstance(message,dict) and message.get('type')=='error':
                            # Provider messages and exception URLs may contain credentials.
                            raise ValueError('Subscription rejected')
                        self.ingest(message);delay=2
            except asyncio.CancelledError:raise
            except Exception as exc:
                with self.lock:self.error='Feed unavailable ('+type(exc).__name__+')'
            finally:
                with self.lock:self.connected=False
            await asyncio.sleep(delay);delay=min(60,delay*2)
