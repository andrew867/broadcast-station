"""Validated, bounded controls for the original study-radio arrangements."""
from pydantic import Field
from .models import StrictModel


class StudyRadioConfig(StrictModel):
    bpm: int = Field(default=80, ge=76, le=84)
    transpose: int = Field(default=0, ge=-5, le=6)
    density: float = Field(default=.72, ge=.25, le=1)
    swing: float = Field(default=.61, ge=.5, le=.66)
    rain: float = Field(default=.04, ge=0, le=1)
    vinyl: float = Field(default=.02, ge=0, le=1)
    melody: float = Field(default=.55, ge=0, le=1)
