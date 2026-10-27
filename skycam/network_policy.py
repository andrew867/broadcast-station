"""Offline preview denies outbound sockets, including calls to local AMCP."""
import os
import socket
from contextvars import ContextVar
import ipaddress


def install_offline_guard():
    if os.environ.get('STATION_OFFLINE','1')=='0':return
    if getattr(socket,'_station_offline_guard',False):return
    original_connect=socket.socket.connect
    original_connect_ex=socket.socket.connect_ex
    original_sendto=socket.socket.sendto
    original_pair=socket.socketpair
    original_dns=socket.getaddrinfo
    making_pair=ContextVar('station_internal_socketpair',default=False)
    def internal_pair(*args,**kwargs):
        token=making_pair.set(True)
        try:return original_pair(*args,**kwargs)
        finally:making_pair.reset(token)
    def blocked(self,*args,**kwargs):
        if self.family in (socket.AF_INET,socket.AF_INET6) and not making_pair.get():
            raise OSError('Outbound networking is disabled in station offline mode')
        return original_connect(self,*args,**kwargs)
    def blocked_ex(self,*args,**kwargs):
        if self.family in (socket.AF_INET,socket.AF_INET6):
            raise OSError('Outbound networking is disabled in station offline mode')
        return original_connect_ex(self,*args,**kwargs)
    def blocked_sendto(self,*args,**kwargs):
        if self.family in (socket.AF_INET,socket.AF_INET6):
            raise OSError('Outbound networking is disabled in station offline mode')
        return original_sendto(self,*args,**kwargs)
    def blocked_dns(*args,**kwargs):
        # Numeric listener resolution has no DNS/network traffic.
        try:ipaddress.ip_address(args[0])
        except (ValueError,IndexError,TypeError):pass
        else:return original_dns(*args,**kwargs)
        raise OSError('DNS lookup is disabled in station offline mode')
    socket.socket.connect=blocked
    socket.socket.connect_ex=blocked_ex
    socket.socket.sendto=blocked_sendto
    socket.getaddrinfo=blocked_dns
    socket.socketpair=internal_pair
    socket._station_offline_guard=True
