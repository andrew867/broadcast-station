"""Display hysteresis, separate from acquisition and program availability."""
from dataclasses import dataclass

@dataclass
class PicturePolicy:
    shown: bool=False
    stable_since: float|None=None
    last_counter: float|None=None
    changes: int=0

    def update(self,now,counter,age,loaded,recovery_mode=0):
        if not loaded or counter is None or (self.last_counter is not None and counter<self.last_counter):
            self.shown=False;self.stable_since=None;self.changes=0
        elif self.last_counter is not None and counter>self.last_counter:self.changes+=1
        self.last_counter=counter
        recent=loaded and counter is not None and age is not None and 0<=age<2.5
        if not recent:self.stable_since=None
        elif self.stable_since is None:self.stable_since=now
        # Already-visible pictures survive brief stalls. Newly acquired pictures
        # need repeated observations, not an open socket or one lucky frame.
        if not self.shown and recent and self.changes>=2 and now-self.stable_since>=2:
            self.shown=True
        if self.shown and age is not None and age<8:
            return 'held' if not recent else 'recovering' if recovery_mode>0 else 'live'
        self.shown=False
        return 'loading'
