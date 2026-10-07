from typing import Any
from pydantic import BaseModel, ConfigDict
from backend.schemas.source import SourceResponse

class FieldValue(BaseModel):
    value: Any = None
    status: str = "AVAILABLE" # AVAILABLE or NOT_FOUND
    reason: str | None = None

class LocationInfo(BaseModel):
    start_location: FieldValue
    end_location: FieldValue
    length_km: FieldValue
    latitude: FieldValue
    longitude: FieldValue
    geometry_wkt: FieldValue

class TimelineInfo(BaseModel):
    appointed_date: FieldValue
    start_date: FieldValue
    expected_completion_date: FieldValue
    actual_completion_date: FieldValue

class FinancialsInfo(BaseModel):
    estimated_cost: FieldValue
    awarded_cost: FieldValue
    execution_mode: FieldValue

class ProgressInfo(BaseModel):
    status: FieldValue
    physical_progress_percentage: FieldValue

class IntelligenceContractorInfo(BaseModel):
    contractor: dict | None = None
    role: str | None = None
    fallback_contact: dict | None = None
    status: str = "AVAILABLE"
    reason: str | None = None

class RoadIntelligenceResponse(BaseModel):
    query: str | None = None
    matched_by: str | None = None # e.g. "PROJECT_NAME", "ROAD_NAME", "LOCATION"
    confidence_score: float = 1.0
    project: dict | FieldValue
    road: dict | FieldValue
    location: LocationInfo
    authorities: list[dict]
    contractors: list[dict] | IntelligenceContractorInfo
    tenders: list[dict]
    timeline: TimelineInfo
    financials: FinancialsInfo
    progress: ProgressInfo
    sources: list[SourceResponse]

    model_config = ConfigDict(from_attributes=True)
