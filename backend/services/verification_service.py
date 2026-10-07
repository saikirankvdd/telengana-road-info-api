from typing import TypeVar, List, Optional, Any
from datetime import datetime, timezone
from backend.schemas.research import (
    EvidentiaryField,
    CandidateValue,
    SourceModel,
    VerificationStatus,
    AuthorityLevel,
    SourceType
)

T = TypeVar("T")

class VerificationService:
    """
    Evaluates raw candidate evidence from multiple sources for a field and determines:
    - Verification status (VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONFLICTING, NOT_FOUND)
    - Consolidated value (or None if conflicting / not found)
    - Confidence score (0.0 to 1.0)
    - Complete evidentiary provenance including historical/competing candidate preservation
    """

    @staticmethod
    def verify_field(
        field_name: str,
        candidates: List[CandidateValue[T]]
    ) -> EvidentiaryField[T]:
        # Filter out candidates with null/empty values or whitespace-only strings
        valid_candidates = []
        for c in candidates:
            if c.value is None:
                continue
            if isinstance(c.value, str) and not c.value.strip():
                continue
            valid_candidates.append(c)

        # Rule: NEVER FABRICATE MISSING VALUES
        if not valid_candidates:
            return EvidentiaryField[T](
                value=None,
                verification_status=VerificationStatus.NOT_FOUND,
                confidence=0.0,
                sources=[],
                candidate_values=[],
                evidence_text=None,
                retrieved_at=datetime.now(timezone.utc).isoformat()
            )

        # Group candidates by normalized string representation of value
        value_groups = {}
        for c in valid_candidates:
            norm_key = str(c.value).strip().lower()
            if norm_key not in value_groups:
                value_groups[norm_key] = {
                    "raw_value": c.value,
                    "candidates": [],
                    "has_primary": False,
                    "max_authority": AuthorityLevel.TERTIARY
                }
            value_groups[norm_key]["candidates"].append(c)
            auth_str = c.source.authority_level.value if hasattr(c.source.authority_level, "value") else str(c.source.authority_level)
            if auth_str == AuthorityLevel.PRIMARY.value:
                value_groups[norm_key]["has_primary"] = True
                value_groups[norm_key]["max_authority"] = AuthorityLevel.PRIMARY
            elif auth_str == AuthorityLevel.SECONDARY.value and value_groups[norm_key]["max_authority"] != AuthorityLevel.PRIMARY:
                value_groups[norm_key]["max_authority"] = AuthorityLevel.SECONDARY

        all_sources = [c.source for c in valid_candidates]

        # Multi-value handling & Conflict Resolution (Rule 3, 5 & 6)
        if len(value_groups) > 1:
            return EvidentiaryField[T](
                value=None,  # Do not force a choice when sources conflict
                verification_status=VerificationStatus.CONFLICTING,
                confidence=0.3,
                sources=all_sources,
                candidate_values=valid_candidates,  # Preserve all historical & competing candidate values
                evidence_text=f"Conflicting values reported across sources for '{field_name}'",
                retrieved_at=datetime.now(timezone.utc).isoformat()
            )

        # Single distinct value group across all sources
        norm_key = list(value_groups.keys())[0]
        group = value_groups[norm_key]
        winning_value = group["raw_value"]
        group_candidates = group["candidates"]

        # Compute confidence and enforce TERTIARY restriction
        has_primary = group["has_primary"]
        num_sources = len(group_candidates)

        # Check if ALL sources supporting this value are TERTIARY
        all_tertiary = all((c.source.authority_level.value if hasattr(c.source.authority_level, "value") else str(c.source.authority_level)) == AuthorityLevel.TERTIARY.value for c in group_candidates)

        if all_tertiary:
            # SECTION 3 RULE: Tertiary evidence alone can NEVER produce VERIFIED status
            status = VerificationStatus.UNVERIFIED
            confidence = min(0.50, 0.30 + (0.10 * num_sources))
        elif has_primary and num_sources >= 2:
            status = VerificationStatus.VERIFIED
            confidence = 0.95
        elif has_primary:
            status = VerificationStatus.VERIFIED
            confidence = 0.85
        elif num_sources >= 2:
            status = VerificationStatus.PARTIALLY_VERIFIED
            confidence = 0.70
        else:
            source_type = group_candidates[0].source.source_type
            if source_type in (SourceType.GOVERNMENT_PORTAL, SourceType.TENDER_PORTAL, SourceType.GOVERNMENT_DOCUMENT, SourceType.GOVERNMENT_ORDER):
                status = VerificationStatus.VERIFIED
                confidence = 0.80
            else:
                status = VerificationStatus.UNVERIFIED
                confidence = 0.50

        primary_snippet = group_candidates[0].evidence_snippet or group_candidates[0].source.evidence_text

        return EvidentiaryField[T](
            value=winning_value,
            verification_status=status,
            confidence=confidence,
            sources=all_sources,
            candidate_values=valid_candidates,
            evidence_text=primary_snippet,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
