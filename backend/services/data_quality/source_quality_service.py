import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from backend.schemas.research import EvidentiaryField, SourceModel, AuthorityLevel
from backend.schemas.data_quality import QualitySeverity, QualityStatus, ValidationIssue

logger = logging.getLogger(__name__)

# Configurable Freshness Policy in Days
FRESHNESS_POLICY_DAYS = {
    "tender_status": 30,
    "submission_deadline": 30,
    "contractor": 90,
    "awarded_cost": 90,
    "estimated_cost": 180,
    "project_name": 365,
    "latitude": 365,
    "longitude": 365,
    "road_number": 365,
    "road_length_km": 365,
}
DEFAULT_FRESHNESS_DAYS = 180


class SourceQualityService:
    """
    Evaluates evidence completeness, source authority ranking, cross-source
    conflicts, unsupported field values, and configurable freshness policies.
    """

    @staticmethod
    def evaluate_field_provenance(
        field_name: str,
        field: EvidentiaryField
    ) -> Tuple[QualityStatus, bool, bool, List[ValidationIssue]]:
        """
        Evaluates source URL presence, authority level, and freshness.
        Returns: (quality_status, is_supported, is_stale, list_of_issues)
        """
        issues: List[ValidationIssue] = []
        if field.value is None or field.verification_status == "NOT_FOUND":
            return QualityStatus.VALID, True, False, issues

        sources = field.sources or []
        if not sources:
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="UNSUPPORTED_FIELD_VALUE",
                severity=QualitySeverity.WARNING,
                description=f"Field '{field_name}' has value '{field.value}' but lacks supporting source evidence",
                current_value=str(field.value)
            ))
            return QualityStatus.UNSUPPORTED, False, False, issues

        # Check if any source has a valid URL
        has_url = any(s.source_url and str(s.source_url).strip() for s in sources)
        has_primary = any(s.authority_level == AuthorityLevel.PRIMARY or str(s.authority_level).upper() == "PRIMARY" for s in sources)

        if not has_url:
            issues.append(ValidationIssue(
                field_name=field_name,
                rule_name="MISSING_SOURCE_URL",
                severity=QualitySeverity.WARNING,
                description=f"Field '{field_name}' sources lack direct source URLs",
                current_value=str(field.value),
                source_references=[s.source_name for s in sources if s.source_name]
            ))
            return QualityStatus.UNSUPPORTED, True, False, issues

        # Check Freshness
        freshness_limit_days = FRESHNESS_POLICY_DAYS.get(field_name, DEFAULT_FRESHNESS_DAYS)
        now_utc = datetime.now(timezone.utc)
        is_stale = False

        if field.retrieved_at:
            try:
                ret_dt = datetime.fromisoformat(field.retrieved_at.replace("Z", "+00:00"))
                if now_utc - ret_dt > timedelta(days=freshness_limit_days):
                    is_stale = True
                    issues.append(ValidationIssue(
                        field_name=field_name,
                        rule_name="STALE_EVIDENCE",
                        severity=QualitySeverity.INFO,
                        description=f"Field '{field_name}' evidence retrieved {ret_dt.strftime('%Y-%m-%d')} exceeds freshness policy ({freshness_limit_days} days)",
                        current_value=str(field.value)
                    ))
            except Exception:
                pass

        return QualityStatus.VALID, True, is_stale, issues

    @staticmethod
    def detect_cross_source_conflicts(
        field_name: str,
        field: EvidentiaryField
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Detects conflicting candidate values across multiple sources for a field.
        """
        issues: List[ValidationIssue] = []
        if field.verification_status != "CONFLICTING" and len(field.candidate_values) <= 1:
            return False, issues

        # Collect candidate details
        candidates_desc = []
        for c in field.candidate_values:
            val_str = str(c.value)
            s_name = c.source.source_name if c.source else "Unknown Source"
            candidates_desc.append(f"'{val_str}' ({s_name})")

        issues.append(ValidationIssue(
            field_name=field_name,
            rule_name="CROSS_SOURCE_CONFLICT",
            severity=QualitySeverity.WARNING,
            description=f"Field '{field_name}' has conflicting values across sources: {', '.join(candidates_desc)}",
            current_value=str(field.value),
            source_references=[c.source.source_url for c in field.candidate_values if c.source and c.source.source_url]
        ))

        return True, issues
