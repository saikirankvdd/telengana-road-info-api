from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from backend.schemas.research import ProjectResearchResult, SourceModel

class MatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE_MATCH = "HIGH_CONFIDENCE_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    NEW_ENTITY = "NEW_ENTITY"
    NO_MATCH = "NO_MATCH"
    CONFLICTING_MATCH = "CONFLICTING_MATCH"

class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"

class FieldComparisonResult(str, Enum):
    MATCHED = "MATCHED"
    PROPOSED_UPDATE = "PROPOSED_UPDATE"
    PROPOSED_INSERT = "PROPOSED_INSERT"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED_MISSING = "UNVERIFIED_MISSING"
    NO_CHANGE = "NO_CHANGE"

class FieldDecision(str, Enum):
    PENDING = "PENDING"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"

class MergeActionType(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    REJECT = "REJECT"
    NO_CHANGE = "NO_CHANGE"

class FieldComparisonDetail(BaseModel):
    field_name: str
    research_value: Optional[Any] = None
    canonical_value: Optional[Any] = None
    comparison_result: FieldComparisonResult = FieldComparisonResult.NO_CHANGE
    verification_status: str = "NOT_FOUND"
    confidence: float = 0.0
    evidence_text: Optional[str] = None
    source_url: Optional[str] = None
    decision: FieldDecision = FieldDecision.PENDING

class EntityResolutionResult(BaseModel):
    review_id: Optional[int] = None
    research_run_id: Optional[int] = None
    project_name_query: str
    match_status: MatchStatus = MatchStatus.NO_MATCH
    match_confidence: float = 0.0
    matching_signals: List[str] = Field(default_factory=list)
    negative_signals: List[str] = Field(default_factory=list)
    candidate_entity_id: Optional[int] = None
    candidate_entity_name: Optional[str] = None
    candidate_entity_type: str = "PROJECT"
    field_comparisons: Dict[str, FieldComparisonDetail] = Field(default_factory=dict)

class ResolveEntityRequest(BaseModel):
    research_run_id: Optional[int] = Field(default=None, description="Database ID of a previous research run")
    project_name: Optional[str] = Field(default=None, description="Project name query if research_run_id is omitted")
    force_refresh: bool = Field(default=False)

class ReviewDecisionRequest(BaseModel):
    field_decisions: Dict[str, FieldDecision] = Field(
        default_factory=dict,
        description="Dictionary mapping field_name to FieldDecision (APPROVE, REJECT, NEEDS_MORE_EVIDENCE)"
    )
    overall_status: Optional[ReviewStatus] = None
    reviewed_by: str = Field(default="admin")
    review_notes: Optional[str] = None

class MergeExecutionRequest(BaseModel):
    approved_by: str = Field(default="admin")
    review_notes: Optional[str] = None

class ResearchMergeActionResponse(BaseModel):
    id: int
    review_id: int
    research_run_id: int
    field_name: str
    target_table: str
    target_record_id: int
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    action: MergeActionType
    approved_by: str
    approved_at: str

class ResearchMergeReviewResponse(BaseModel):
    id: int
    research_run_id: int
    candidate_entity_type: str
    candidate_entity_id: Optional[int] = None
    match_status: MatchStatus
    match_confidence: float
    matching_signals: List[str]
    negative_signals: List[str]
    field_comparison: Dict[str, Any]
    field_decisions: Dict[str, str]
    review_status: ReviewStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: str
