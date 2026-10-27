"""Durable small configuration writes; generated frame caches remain separate."""
import json,os,tempfile

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    name=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
            name=f.name;json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(name,path);name=None
        if os.name!='nt':
            fd=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    finally:
        if name:os.unlink(name)
