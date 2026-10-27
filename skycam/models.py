from pydantic import BaseModel, Field, ConfigDict, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Site(StrictModel):
    lat: float = Field(default=0, ge=-90, le=90)
    lon: float = Field(default=0, ge=-180, le=180)
    altitude_msl_m: float = Field(default=0, ge=-500, le=9000)
    geoid_separation_m: float | None = Field(default=None, ge=-150, le=150)
    verified: bool = False


class Landmark(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    altitude_msl_m: float = Field(ge=-500, le=9000)
    geoid_separation_m: float | None = Field(default=None, ge=-150, le=150)
    validation: bool = False


class CameraRequest(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    width: int = Field(default=1920, ge=320, le=7680)
    height: int = Field(default=1080, ge=180, le=4320)
    site: Site = Field(default_factory=Site)
    initial_hfov_deg: float = Field(default=80, ge=20, le=150)
    fit_distortion: bool = True
    video_delay_s: float = Field(default=1.5, ge=0, le=30)
    approved: bool = False
    reference_only: bool = False
    landmarks: list[Landmark] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def coordinates_inside_image(self):
        if any(p.x >= self.width or p.y >= self.height for p in self.landmarks):
            raise ValueError('Landmark pixels must be inside the native image dimensions')
        return self
