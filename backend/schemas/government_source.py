from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.schemas.research import AuthorityLevel, SourceType

class GovernmentSourceType(str, Enum):
    OFFICIAL_GOVERNMENT_PORTAL = "OFFICIAL_GOVERNMENT_PORTAL"
    OFFICIAL_API = "OFFICIAL_API"
    OFFICIAL_OPEN_DATA = "OFFICIAL_OPEN_DATA"
    OFFICIAL_GIS = "OFFICIAL_GIS"
    PROCUREMENT_PORTAL = "PROCUREMENT_PORTAL"
    GOVERNMENT_ORDER_PORTAL = "GOVERNMENT_ORDER_PORTAL"
    PUBLIC_WEB_SOURCE = "PUBLIC_WEB_SOURCE"
    NEWS_SOURCE = "NEWS_SOURCE"

class LegalAccessStatus(str, Enum):
    PUBLIC_ACCESSIBLE = "PUBLIC_ACCESSIBLE"
    RESTRICTED = "RESTRICTED"
    NOT_ACCESSIBLE = "NOT_ACCESSIBLE"
    RATE_LIMITED = "RATE_LIMITED"
    CAPTCHA_PROTECTED = "CAPTCHA_PROTECTED"

class ProjectDomain(str, Enum):
    NATIONAL_HIGHWAY = "NATIONAL_HIGHWAY"
    MUNICIPAL = "MUNICIPAL"
    HMDA_INFRASTRUCTURE = "HMDA_INFRASTRUCTURE"
    RURAL_ROAD = "RURAL_ROAD"
    GOVERNMENT_ORDER = "GOVERNMENT_ORDER"
    CENTRAL_INSTITUTION = "CENTRAL_INSTITUTION"
    STATE_HIGHWAY = "STATE_HIGHWAY"
    GENERIC = "GENERIC"

class GovernmentSource(BaseModel):
    source_id: str = Field(..., description="Unique alphanumeric identifier for the source")
    name: str = Field(..., description="Human readable name of the government source")
    base_url: str = Field(..., description="Root URL or endpoint of the source")
    source_type: GovernmentSourceType = Field(default=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL)
    authority_level: AuthorityLevel = Field(default=AuthorityLevel.PRIMARY)
    state: Optional[str] = Field(default="Telangana")
    department: Optional[str] = Field(default=None)
    supported_domains: List[ProjectDomain] = Field(default_factory=list)
    supported_data_types: List[str] = Field(default_factory=list)
    access_method: str = Field(default="API", description="API, WEB_SCRAPE, GIS_WMS, RSS")
    enabled: bool = Field(default=True)
    priority: int = Field(default=1, description="Priority rank (1 = highest)")
    legal_access_status: LegalAccessStatus = Field(default=LegalAccessStatus.PUBLIC_ACCESSIBLE)

class FieldSourcePreference(BaseModel):
    field_name: str
    preferred_source_types: List[GovernmentSourceType]
    preferred_authority_level: AuthorityLevel = AuthorityLevel.PRIMARY
