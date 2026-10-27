"""Bounded camera transport evidence, separate from a decoder's frame counter."""
import re

LOSS=re.compile(r'\[path ([A-Za-z0-9_/-]+)\].*?(\d+) RTP packets lost')

def observe_loss(rows,line,now):
    match=LOSS.search(line)
    if not match:return False
    name,count=match[1],int(match[2])
    previous=rows.get(name,{})
    rows[name]={'last_loss_at':now,'lost_packets':previous.get('lost_packets',0)+count}
    return True

def transport_fault(row,recovered_at,now,quiet_seconds=5):
    """After known packet loss require quiet transport and a new decoder.

    This only detects reported transport loss, not arbitrary damaged pixels.
    A new decoder must still deliver recent video before being shown.
    """
    last=(row or {}).get('last_loss_at',0)
    if not last or last<=recovered_at:return None
    return 'wait' if now-last<quiet_seconds else 'reload'
