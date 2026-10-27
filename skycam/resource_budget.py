"""Observe native cache budgets without bulk collection or output restarts."""
import time
import xml.etree.ElementTree as ET

MIB=1024*1024

def pool_sizes(reply):
    root=ET.fromstring(reply[reply.index('<?xml'):])
    def number(path):
        node=root.find('summary/'+path)
        if node is None:raise ValueError('Missing graphics pool measurement')
        return max(0,int(node.text))
    return {'budget_per_pool_bytes':int(root.findtext('summary/cache_budget_bytes','0')),
            'device_bytes':number('pooled_device_buffers/total_size'),
            'host_bytes':number('pooled_host_buffers/total_read_size')+number('pooled_host_buffers/total_write_size'),
            'allocated_read_bytes':number('all_host_buffers/total_read_size'),
            'cache_policy':root.findtext('summary/cache_policy','legacy'),
            'device_evictions':int(root.findtext('summary/device_evictions','0')),
            'host_evictions':int(root.findtext('summary/host_evictions','0'))}

class GraphicsBudget:
    def __init__(self):
        self.last_check=-1000;self.status={}
    def check(self,command,now=None):
        now=time.monotonic() if now is None else now
        if now-self.last_check<30:return self.status
        self.last_check=now
        try:
            pools=pool_sizes(command('GL INFO',xml=True))
            self.status.update(pools,checked_at=time.time(),error=None)
            if not pools['budget_per_pool_bytes']:
                self.status['error']='Native graphics cache limit is unavailable'
        except (OSError,RuntimeError,ValueError,ET.ParseError) as exc:
            self.status.update(error=str(exc)[:160],checked_at=time.time())
        return self.status
