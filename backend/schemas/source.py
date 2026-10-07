from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SourceBase(BaseModel):
    source_name: str
    source_type: str
    source_url: str | None = None
    source_record_id: str | None = None

class SourceCreate(SourceBase):
    pass

class SourceResponse(SourceBase):
    id: int
    retrieved_at: datetime
    last_verified_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
