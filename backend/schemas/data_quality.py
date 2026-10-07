from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QualitySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class QualityStatus(str, Enum):
    VALID = "VALID"
    SUSPICIOUS = "SUSPICIOUS"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"
    QUARANTINED = "QUARANTINED"


class QualityClass(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    INVALID = "INVALID"
    QUARANTINED = "QUARANTINED"


class ValidationIssue(BaseModel):
    field_name: str
    rule_name: str
    severity: QualitySeverity
    description: str
    current_value: Optional[Any] = None
    source_references: List[str] = Field(default_factory=list)


class FieldQualityReport(BaseModel):
    field_name: str
    value: Optional[Any] = None
    verification_status: str
    quality_status: QualityStatus
    quality_score: float = 1.0
    issues: List[ValidationIssue] = Field(default_factory=list)
    sources_count: int = 0
    has_primary_source: bool = False
    is_stale: bool = False


class DuplicateCandidateSummary(BaseModel):
    candidate_id: int
    project_name: str
    match_score: float
    matching_signals: List[str] = Field(default_factory=list)
    conflicting_signals: List[str] = Field(default_factory=list)


class ResearchQualityReportResponse(BaseModel):
    id: Optional[int] = None
    research_run_id: Optional[int] = None
    project_name: str
    overall_quality_score: float
    quality_class: QualityClass
    fields_checked: int
    fields_valid: int
    fields_suspicious: int
    fields_invalid: int
    fields_missing: int
    fields_unsupported: int
    cross_source_conflicts: int
    duplicate_candidates_count: int
    stale_fields_count: int
    merge_eligible: bool
    merge_blockers: List[str] = Field(default_factory=list)
    is_quarantined: bool = False
    issues: List[ValidationIssue] = Field(default_factory=list)
    evaluated_at: str


class ValidationRequest(BaseModel):
    research_run_id: Optional[int] = None
    project_name: Optional[str] = None
    force_refresh: bool = False
