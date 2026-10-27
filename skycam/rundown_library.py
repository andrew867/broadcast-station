"""Operator-owned named playlists, separate from the active rundown."""
import json,threading,time,uuid
from pydantic import Field,field_validator
from .models import StrictModel
from .rundown import RundownConfig

class LibraryWrite(StrictModel):
    name:str=Field(min_length=1,max_length=64)
    config:RundownConfig
    expected_revision:int=Field(ge=0)
    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if not value or any(ord(c)<32 for c in value):raise ValueError('Use a visible rundown name')
        return value

class LibraryRevision(StrictModel):
    expected_revision:int=Field(ge=0)

class LibraryRecord(StrictModel):
    id:str=Field(pattern=r'^[a-f0-9]{32}$')
    name:str=Field(min_length=1,max_length=64)
    config:RundownConfig
    updated_at:float

class LibraryDocument(StrictModel):
    version:int=1
    revision:int=Field(default=0,ge=0)
    items:list[LibraryRecord]=Field(default_factory=list,max_length=50)
    history:list[list[LibraryRecord]]=Field(default_factory=list,max_length=20)

class LibraryConflict(ValueError):pass

class RundownLibrary:
    def __init__(self,data):
        self.path=data/'broadcast/rundown-library.json';self.lock=threading.RLock();self.error=None
        self.document=LibraryDocument()
        if self.path.exists():
            try:
                self.document=LibraryDocument.model_validate_json(self.path.read_text(encoding='utf-8'))
                if self.document.version!=1:raise ValueError('Unsupported library format')
            except (OSError,ValueError):self.error='Saved rundown library could not be read. Restore its backup before editing; the live rundown is unaffected.'
    def _ready(self):
        if self.error:raise RuntimeError(self.error)
    def public(self):
        with self.lock:
            self._ready()
            return {'revision':self.document.revision,'items':[r.model_dump() for r in self.document.items],
                    'can_undo':bool(self.document.history)}
    def _revision(self,revision):
        self._ready()
        if revision!=self.document.revision:raise LibraryConflict('The library changed in another window. Reload it before saving.')
    def _commit(self,items,undo=False):
        previous=self.document
        history=previous.history[:-1] if undo else [*previous.history,previous.items][-20:]
        next_document=LibraryDocument(revision=previous.revision+1,items=items,history=history)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(next_document.model_dump_json(indent=2),encoding='utf-8');tmp.replace(self.path)
        self.document=next_document
    def save(self,body,item_id=None):
        with self.lock:
            self._revision(body.expected_revision)
            if item_id is not None and not any(r.id==item_id for r in self.document.items):raise KeyError('Saved rundown not found')
            if any(r.name.casefold()==body.name.casefold() and r.id!=item_id for r in self.document.items):raise ValueError('That name is already used. Choose a different name.')
            if item_id is None and len(self.document.items)>=50:raise ValueError('The library holds up to 50 rundowns')
            record=LibraryRecord(id=item_id or uuid.uuid4().hex,name=body.name,config=body.config,updated_at=time.time())
            items=[record if r.id==item_id else r for r in self.document.items]
            if item_id is None:items.append(record)
            self._commit(items)
            return {'saved_id':record.id,**self.public()}
    def delete(self,item_id,revision):
        with self.lock:
            self._revision(revision)
            items=[r for r in self.document.items if r.id!=item_id]
            if len(items)==len(self.document.items):raise KeyError('Saved rundown not found')
            self._commit(items);return self.public()
    def undo(self,revision):
        with self.lock:
            self._revision(revision)
            if not self.document.history:raise ValueError('No library change to undo')
            self._commit(self.document.history[-1],undo=True);return self.public()
    def export(self,item_id):
        with self.lock:
            self._ready()
            record=next((r for r in self.document.items if r.id==item_id),None)
            if record is None:raise KeyError('Saved rundown not found')
            return {'format':'skycam-rundown','version':1,'name':record.name,'config':record.config.model_dump()}
