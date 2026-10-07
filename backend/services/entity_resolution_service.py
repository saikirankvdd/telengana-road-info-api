import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.schemas.research import ProjectResearchResult, ProjectResearchData, VerificationStatus
from backend.schemas.research_merge import (
    EntityResolutionResult,
    FieldComparisonDetail,
    FieldComparisonResult,
    MatchStatus,
    FieldDecision
)
from backend.models.project import Project, ProjectAuthority, ProjectContractor, ProjectTender
from backend.models.tender import Tender
from backend.models.contract import Contract
from backend.models.contractor import Contractor
from backend.models.authority import Authority
from backend.models.road import Road
from backend.models.project_location import ProjectLocation
from backend.models.history import ProjectIdentifier
from backend.models.research import ResearchRun
from backend.models.research_merge import ResearchMergeReview

logger = logging.getLogger(__name__)

def normalize_string(val: Optional[str]) -> str:
    if not val:
        return ""
    # Strip punctuation and common prefixes/suffixes for clean comparison
    cleaned = "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in val)
    words = [w for w in cleaned.split() if w not in ("project", "corridor", "road", "telangana", "of", "and", "the", "at", "to", "in")]
    return " ".join(words)

def compute_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in km between two lat/lon pairs."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class EntityResolutionService:
    def __init__(self, db: Session):
        self.db = db

    def resolve(
        self,
        research_result: ProjectResearchResult,
        research_run_id: Optional[int] = None
    ) -> EntityResolutionResult:
        query_name = research_result.project_name_query
        p_data = research_result.project

        # Candidate canonical projects evaluation
        all_projects = self.db.query(Project).all()
        best_candidate: Optional[Project] = None
        best_score: float = 0.0
        best_matching_signals: List[str] = []
        best_negative_signals: List[str] = []

        res_govt_id = p_data.government_project_id.value or p_data.project_id.value
        res_tender_id = p_data.tender_id.value
        res_ref_num = p_data.reference_number.value
        res_contractor = p_data.contractor.value
        res_authority = p_data.authority.value
        res_district = p_data.district.value
        res_lat = p_data.latitude.value
        res_lon = p_data.longitude.value
        res_road_num = p_data.road_number.value

        norm_query_name = normalize_string(query_name)

        for proj in all_projects:
            score = 0.0
            matching = []
            negative = []

            # 1. Government project identifier match
            if res_govt_id:
                # Check ProjectIdentifier history table
                pid_match = self.db.query(ProjectIdentifier).filter(
                    ProjectIdentifier.project_id == proj.id,
                    ProjectIdentifier.identifier_value == res_govt_id
                ).first()
                if pid_match or proj.project_id == res_govt_id:
                    score += 0.95
                    matching.append(f"Exact Government Project ID Match ('{res_govt_id}')")

            # 2. Exact tender ID match
            if res_tender_id:
                t_match = self.db.query(ProjectTender).join(Tender).filter(
                    ProjectTender.project_id == proj.id,
                    Tender.tender_id == res_tender_id
                ).first()
                if t_match:
                    score += 0.90
                    matching.append(f"Exact Tender ID Match ('{res_tender_id}')")

            # 3. Exact tender reference number match
            if res_ref_num:
                ref_match = self.db.query(ProjectTender).join(Tender).filter(
                    ProjectTender.project_id == proj.id,
                    Tender.reference_number == res_ref_num
                ).first()
                if ref_match:
                    score += 0.85
                    matching.append(f"Exact Tender Reference Number Match ('{res_ref_num}')")

            # 4. Normalized project name match & Fuzzy title similarity match
            proj_norm_name = normalize_string(proj.normalized_project_name) or normalize_string(proj.project_name)
            if norm_query_name and proj_norm_name:
                if norm_query_name == proj_norm_name:
                    score += 0.85
                    matching.append(f"Exact Normalized Name Match ('{proj.project_name}')")
                elif norm_query_name in proj_norm_name or proj_norm_name in norm_query_name:
                    score += 0.45
                    matching.append(f"Sub-string Name Similarity Match ('{proj.project_name}')")
                else:
                    ratio = SequenceMatcher(None, norm_query_name, proj_norm_name).ratio()
                    if ratio >= 0.50:
                        score += round(0.50 * ratio, 2)
                        matching.append(f"Fuzzy Name Similarity ({int(ratio*100)}% match with '{proj.project_name}')")

            # 7. Authority match
            if res_authority and proj.authority_id:
                auth = self.db.query(Authority).filter(Authority.id == proj.authority_id).first()
                if auth and auth.name and normalize_string(auth.name) == normalize_string(res_authority):
                    score += 0.10
                    matching.append(f"Authority Match ('{auth.name}')")

            # 8. Contractor match
            if res_contractor:
                c_match = self.db.query(ProjectContractor).join(Contractor).filter(
                    ProjectContractor.project_id == proj.id,
                    func.lower(Contractor.legal_name).contains(res_contractor.lower())
                ).first()
                if c_match:
                    score += 0.15
                    matching.append(f"Contractor Match ('{res_contractor}')")

            # 9. District / location match
            if res_district:
                loc_match = self.db.query(ProjectLocation).filter(
                    ProjectLocation.project_id == proj.id,
                    func.lower(ProjectLocation.district) == res_district.lower()
                ).first()
                if loc_match:
                    score += 0.10
                    matching.append(f"District Match ('{res_district}')")
                else:
                    loc_diff = self.db.query(ProjectLocation).filter(ProjectLocation.project_id == proj.id).first()
                    if loc_diff and loc_diff.district and loc_diff.district.lower() != res_district.lower():
                        score -= 0.20
                        negative.append(f"District Discrepancy (Canonical: {loc_diff.district}, Researched: {res_district})")

            # 11. Geographic spatial proximity check
            if res_lat is not None and res_lon is not None:
                loc_spatial = self.db.query(ProjectLocation).filter(
                    ProjectLocation.project_id == proj.id,
                    ProjectLocation.latitude.isnot(None),
                    ProjectLocation.longitude.isnot(None)
                ).first()
                if loc_spatial:
                    dist = compute_haversine_distance(res_lat, res_lon, loc_spatial.latitude, loc_spatial.longitude)
                    if dist <= 2.0: # Within 2km radius
                        score += 0.35
                        matching.append(f"Geographic Proximity Match ({dist:.2f} km)")
                    elif dist > 50.0:
                        score -= 0.30
                        negative.append(f"Geographic Distance (> {dist:.1f} km)")

            # Cap final score between 0.0 and 1.0
            score = max(0.0, min(1.0, score))

            if score > best_score:
                best_score = score
                best_candidate = proj
                best_matching_signals = matching
                best_negative_signals = negative

        # Determine Match Status based on confidence thresholds
        if best_score >= 0.90:
            status = MatchStatus.EXACT_MATCH if any("Exact" in s for s in best_matching_signals) else MatchStatus.HIGH_CONFIDENCE_MATCH
        elif best_score >= 0.75:
            status = MatchStatus.HIGH_CONFIDENCE_MATCH
        elif best_score >= 0.60:
            status = MatchStatus.POSSIBLE_MATCH
        else:
            status = MatchStatus.NEW_ENTITY if best_score == 0.0 else MatchStatus.NO_MATCH

        # Perform Field-Level Comparison against best candidate (or empty canonical baseline)
        field_comparisons = self.compare_fields(p_data, best_candidate)

        # Build EntityResolutionResult
        res_run_id = research_run_id or (int(research_result.project_id) if research_result.project_id and research_result.project_id.isdigit() else None)

        result = EntityResolutionResult(
            research_run_id=res_run_id,
            project_name_query=query_name,
            match_status=status,
            match_confidence=round(best_score, 4),
            matching_signals=best_matching_signals,
            negative_signals=best_negative_signals,
            candidate_entity_id=best_candidate.id if best_candidate else None,
            candidate_entity_name=best_candidate.project_name if best_candidate else None,
            candidate_entity_type="PROJECT",
            field_comparisons=field_comparisons
        )

        # Save or update ResearchMergeReview record in database
        if res_run_id:
            review = self.persist_merge_review(res_run_id, result)
            result.review_id = review.id

        return result

    def compare_fields(
        self,
        p_data: ProjectResearchData,
        canonical_proj: Optional[Project]
    ) -> Dict[str, FieldComparisonDetail]:
        comparisons: Dict[str, FieldComparisonDetail] = {}

        # Extract canonical values if candidate project exists
        can_values = {}
        if canonical_proj:
            can_values["project_name"] = canonical_proj.project_name
            can_values["project_id"] = canonical_proj.project_id
            can_values["estimated_cost"] = canonical_proj.estimated_cost
            can_values["awarded_cost"] = canonical_proj.awarded_cost
            can_values["project_length"] = canonical_proj.length_km
            can_values["status"] = canonical_proj.status
            
            # Relationships
            if canonical_proj.contractor_associations:
                can_values["contractor"] = canonical_proj.contractor_associations[0].contractor.legal_name
            if canonical_proj.authority:
                can_values["authority"] = canonical_proj.authority.name
            if canonical_proj.locations:
                loc = canonical_proj.locations[0]
                can_values["district"] = loc.district
                can_values["locality"] = loc.locality
                can_values["location"] = loc.locality or loc.address_text
                can_values["latitude"] = loc.latitude
                can_values["longitude"] = loc.longitude

        for field_name, field_obj in p_data:
            res_val = field_obj.value
            can_val = can_values.get(field_name)
            ver_status = field_obj.verification_status.value
            conf = field_obj.confidence
            evidence_text = field_obj.evidence_text
            source_url = field_obj.sources[0].source_url if field_obj.sources else None

            comp_result = FieldComparisonResult.NO_CHANGE

            if res_val is None or ver_status == "NOT_FOUND":
                comp_result = FieldComparisonResult.UNVERIFIED_MISSING
            elif can_val is None:
                comp_result = FieldComparisonResult.PROPOSED_INSERT if not canonical_proj else FieldComparisonResult.PROPOSED_UPDATE
            else:
                # Compare canonical value vs research value
                norm_res = str(res_val).strip().lower()
                norm_can = str(can_val).strip().lower()
                if norm_res == norm_can:
                    comp_result = FieldComparisonResult.MATCHED
                else:
                    comp_result = FieldComparisonResult.CONFLICTING

            comparisons[field_name] = FieldComparisonDetail(
                field_name=field_name,
                research_value=res_val,
                canonical_value=can_val,
                comparison_result=comp_result,
                verification_status=ver_status,
                confidence=conf,
                evidence_text=evidence_text,
                source_url=source_url,
                decision=FieldDecision.PENDING
            )

        return comparisons

    def persist_merge_review(
        self,
        research_run_id: int,
        res: EntityResolutionResult
    ) -> ResearchMergeReview:
        # Check if review already exists for research run
        review = self.db.query(ResearchMergeReview).filter(
            ResearchMergeReview.research_run_id == research_run_id
        ).first()

        field_comp_dict = {k: v.model_dump() for k, v in res.field_comparisons.items()}
        field_decisions = {k: v.decision.value for k, v in res.field_comparisons.items()}

        if not review:
            review = ResearchMergeReview(
                research_run_id=research_run_id,
                candidate_entity_type=res.candidate_entity_type,
                candidate_entity_id=res.candidate_entity_id,
                match_status=res.match_status.value,
                match_confidence=res.match_confidence,
                matching_signals=res.matching_signals,
                negative_signals=res.negative_signals,
                field_comparison=field_comp_dict,
                field_decisions=field_decisions,
                review_status="PENDING"
            )
            self.db.add(review)
        else:
            review.match_status = res.match_status.value
            review.match_confidence = res.match_confidence
            review.matching_signals = res.matching_signals
            review.negative_signals = res.negative_signals
            review.candidate_entity_id = res.candidate_entity_id
            review.field_comparison = field_comp_dict
            if not review.field_decisions:
                review.field_decisions = field_decisions

        self.db.commit()
        return review
