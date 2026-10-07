from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.schemas.source import SourceResponse
from backend.schemas.road import RoadResponse
from backend.schemas.authority import ProjectAuthorityResponse
from backend.schemas.contractor import ProjectContractorResponse
from backend.schemas.tender import TenderResponse

class ProjectBase(BaseModel):
    project_id: str
    project_name: str
    description: str | None = None
    project_type: str | None = None
    start_location: str | None = None
    end_location: str | None = None
    length_km: float | None = None
    estimated_cost: float | None = None
    awarded_cost: float | None = None
    appointed_date: datetime | None = None
    start_date: datetime | None = None
    expected_completion_date: datetime | None = None
    actual_completion_date: datetime | None = None
    status: str | None = None
    physical_progress: float | None = None
    execution_mode: str | None = None
    geometry_wkt: str | None = None
    source_url: str | None = None

class ProjectCreate(ProjectBase):
    road_id: int | None = None
    source_id: int | None = None

class ProjectResponse(ProjectBase):
    id: int
    road_id: int | None = None
    source_id: int | None = None
    created_at: datetime
    updated_at: datetime
    road: RoadResponse | None = None
    source: SourceResponse | None = None
    authorities: list[ProjectAuthorityResponse] = []
    contractors: list[ProjectContractorResponse] = []
    tenders: list[TenderResponse] = []

    model_config = ConfigDict(from_attributes=True)
