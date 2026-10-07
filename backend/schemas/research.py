from enum import Enum
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    NOT_FOUND = "NOT_FOUND"

class RetrievalStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    RETRIEVED = "RETRIEVED"
    FAILED = "FAILED"


class SourceType(str, Enum):
    GOVERNMENT_PORTAL = "government_portal"
    TENDER_PORTAL = "tender_portal"
    GOVERNMENT_DOCUMENT = "government_document"
    GOVERNMENT_ORDER = "government_order"
    OFFICIAL_COMPANY = "official_company"
    OFFICIAL_PROJECT_PAGE = "official_project_page"
    NEWS_MEDIA = "news_media"
    RESEARCH = "research"
    OTHER = "other"

class AuthorityLevel(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"

class ResearchStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    FAILED = "FAILED"

# ---------------------------------------------------------------------------
# Source & Evidence Models
# ---------------------------------------------------------------------------

class SourceModel(BaseModel):
    source_id: Optional[str] = Field(default=None, description="Unique identifier for the source")
    source_url: Optional[str] = Field(default=None, description="Full URL of the source page or document")
    source_name: str = Field(description="Human readable name of the source")
    source_type: SourceType = Field(default=SourceType.OTHER, description="Classification of source type")
    publisher: Optional[str] = Field(default=None, description="Publishing entity/organization")
    title: Optional[str] = Field(default=None, description="Title of document or article")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when source was accessed"
    )
    evidence_text: Optional[str] = Field(default=None, description="Verbatim text snippet from source")
    document_date: Optional[str] = Field(default=None, description="Date of original document if known")
    authority_level: AuthorityLevel = Field(default=AuthorityLevel.SECONDARY, description="Trust rank of source")
    page: Optional[int] = Field(default=None, description="Page number of document where evidence was found (e.g. PDF page)")

T = TypeVar("T")

class CandidateValue(BaseModel, Generic[T]):
    value: Optional[T] = None
    source: SourceModel
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_snippet: Optional[str] = None

class EvidentiaryField(BaseModel, Generic[T]):
    value: Optional[T] = Field(default=None, description="Extracted field value")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.NOT_FOUND,
        description="Explicit verification state"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence score (0.0 - 1.0)")
    sources: List[SourceModel] = Field(default_factory=list, description="List of supporting or conflicting sources")
    candidate_values: List[CandidateValue[T]] = Field(default_factory=list, description="All raw candidate values gathered")
    evidence_text: Optional[str] = Field(default=None, description="Primary evidence snippet supporting value")
    retrieved_at: Optional[str] = Field(default=None, description="Timestamp of retrieval")

    @classmethod
    def empty(cls) -> "EvidentiaryField[T]":
        return cls(
            value=None,
            verification_status=VerificationStatus.NOT_FOUND,
            confidence=0.0,
            sources=[],
            candidate_values=[]
        )

# ---------------------------------------------------------------------------
# Project Research Data Schema
# ---------------------------------------------------------------------------

class ProjectResearchData(BaseModel):
    project_name: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    project_id: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    government_project_id: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    tender_id: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    reference_number: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    tender_reference: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    tender_publication_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    publication_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    tender_closing_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    submission_deadline: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    award_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    awarded_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    government_order_number: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    government_order_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    authority: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    department: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    contractor: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    contractor_registration: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    estimated_cost: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)
    tender_value: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)
    awarded_cost: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)

    project_length: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)
    road_length_km: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)
    lanes: EvidentiaryField[int] = Field(default_factory=EvidentiaryField.empty)
    number_of_lanes: EvidentiaryField[int] = Field(default_factory=EvidentiaryField.empty)

    location: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    district: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    mandal: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    constituency: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    start_point: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    end_point: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    start_chainage: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    end_chainage: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    latitude: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)
    longitude: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)

    status: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    completion_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    contract_start_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    contract_end_date: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    work_order_number: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    funding_agency: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    road_number: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    dpr_reference: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)

    physical_progress: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    financial_progress: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    delay_reason: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    execution_mode: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    road_structure: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    foundation: EvidentiaryField[str] = Field(default_factory=EvidentiaryField.empty)
    viaduct_length: EvidentiaryField[float] = Field(default_factory=EvidentiaryField.empty)

# ---------------------------------------------------------------------------
# Metadata & Top-level Research Result Models
# ---------------------------------------------------------------------------

class ResearchMetadata(BaseModel):
    searched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    research_duration: float = Field(default=0.0, description="Duration in seconds")
    sources_checked: int = Field(default=0)
    sources_successfully_accessed: int = Field(default=0)
    sources_selected: int = Field(default=0)
    sources_attempted: int = Field(default=0)
    sources_accessed: int = Field(default=0)
    sources_failed: int = Field(default=0)
    sources_not_accessible: int = Field(default=0)
    source_results_found: int = Field(default=0)
    source_results_used: int = Field(default=0)
    fields_requested: int = Field(default=0)
    fields_found: int = Field(default=0)
    fields_verified: int = Field(default=0)
    fields_unverified: int = Field(default=0)
    fields_not_found: int = Field(default=0)
    conflicts_found: int = Field(default=0)
    research_status: ResearchStatus = Field(default=ResearchStatus.NOT_IMPLEMENTED)

class ProjectResearchRequest(BaseModel):
    project_name: str = Field(..., min_length=2, description="Target project name to research")
    force_refresh: bool = Field(default=False, description="Bypass cache and force fresh research execution")

class ProjectResearchResult(BaseModel):
    project_id: Optional[str] = Field(default=None)
    project_name_query: str
    project: ProjectResearchData = Field(default_factory=ProjectResearchData)
    sources: List[SourceModel] = Field(default_factory=list)
    field_verifications: Dict[str, VerificationStatus] = Field(default_factory=dict)
    research_metadata: ResearchMetadata = Field(default_factory=ResearchMetadata)
