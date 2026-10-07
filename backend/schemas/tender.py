from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.schemas.source import SourceResponse

class TenderBase(BaseModel):
    tender_id: str
    tender_reference_number: str | None = None
    title: str
    description: str | None = None
    organisation: str | None = None
    department: str | None = None
    published_date: datetime | None = None
    closing_date: datetime | None = None
    estimated_value: float | None = None
    awarded_value: float | None = None
    status: str | None = None
    source_url: str | None = None

class TenderCreate(TenderBase):
    source_id: int | None = None

class TenderResponse(TenderBase):
    id: int
    source_id: int | None = None
    source: SourceResponse | None = None

    model_config = ConfigDict(from_attributes=True)
