from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.schemas.source import SourceResponse

class RoadBase(BaseModel):
    road_name: str
    road_number: str | None = None
    road_type: str | None = None
    geometry_wkt: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_url: str | None = None

class RoadCreate(RoadBase):
    source_id: int | None = None

class RoadResponse(RoadBase):
    id: int
    source_id: int | None = None
    last_updated: datetime
    source: SourceResponse | None = None

    model_config = ConfigDict(from_attributes=True)
