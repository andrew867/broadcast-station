import importlib.util
from pathlib import Path
import pytest

class Stream:
    def __init__(self,parts):self.parts=iter(parts)
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def settimeout(self,*a):pass
    def sendall(self,*a):pass
    def recv(self,*a):return next(self.parts,b'')

@pytest.mark.parametrize('filename,function,args',[
    ('tools/station_watchdog.py','frame_counter',(5250,)),
    ('deploy/program-watchdog.py','output_frame',()),
])
def test_nested_channel_end_is_not_end_of_fragmented_reply(monkeypatch,filename,function,args):
    path=Path(__file__).parents[1]/filename
    spec=importlib.util.spec_from_file_location('fragmented_guard_'+function,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    fragments=[b'201 INFO OK\r\n<?xml version="1.0"?><channel><stage><channel>2</channel>',
               b'</stage><output><port><port_1><file><frame>1234</frame></file></port_1></port></output></channel>\r\n']
    monkeypatch.setattr(mod.socket,'create_connection',lambda *a,**kw:Stream(fragments))
    assert getattr(mod,function)(*args)==1234
