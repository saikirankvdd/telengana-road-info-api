import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.schemas.research import ProjectResearchResult, ProjectResearchData, EvidentiaryField
from backend.schemas.data_quality import (
    QualitySeverity,
    QualityStatus,
    QualityClass,
    ValidationIssue,
    FieldQualityReport,
    ResearchQualityReportResponse
)
from backend.models.research import ResearchRun
from backend.models.data_quality import (
    ResearchQualityReportModel,
    ResearchQualityIssueModel,
    ResearchDuplicateCandidateModel
)
from backend.services.data_quality.field_validator import FieldValidator
from backend.services.data_quality.cross_field_validator import CrossFieldValidator
from backend.services.data_quality.source_quality_service import SourceQualityService
from backend.services.data_quality.duplicate_detector import DuplicateDetector

logger = logging.getLogger(__name__)


class DataQualityService:
    """
    Main Data Quality & Validation Framework coordinator.
    Evaluates research results, detects anomalies, calculates quality scores,
    determines merge eligibility, handles quarantine, and persists audit reports.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def validate_research_result(
        self,
        research_result: ProjectResearchResult,
        research_run_id: Optional[int] = None
    ) -> ResearchQualityReportResponse:
        project_name = research_result.project_name_query
        p_data = research_result.project

        issues: List[ValidationIssue] = []
        field_reports: List[FieldQualityReport] = []

        fields_checked = 0
        fields_valid = 0
        fields_suspicious = 0
        fields_invalid = 0
        fields_missing = 0
        fields_unsupported = 0
        cross_source_conflicts = 0
        stale_fields_count = 0

        # Iterating over all fields in ProjectResearchData
        field_names = [
            "project_name", "project_id", "description", "authority", "department",
            "district", "constituency", "road_number", "road_length_km", "latitude",
            "longitude", "tender_id", "tender_reference", "publication_date",
            "submission_deadline", "awarded_date", "contract_start_date",
            "contract_end_date", "estimated_cost", "awarded_cost", "contractor",
            "government_order_number", "status"
        ]

        est_cost_val = p_data.estimated_cost.value if p_data.estimated_cost else None

        for fname in field_names:
            ev_field: Optional[EvidentiaryField] = getattr(p_data, fname, None)
            if not ev_field:
                fields_missing += 1
                continue

            val = ev_field.value
            fields_checked += 1

            if val is None or ev_field.verification_status == "NOT_FOUND":
                fields_missing += 1
                continue

            # 1. Field-Level Validation
            f_status = QualityStatus.VALID

            # String validation
            if isinstance(val, str):
                str_status, str_issues, norm_val = FieldValidator.validate_string(fname, val)
                if str_issues:
                    issues.extend(str_issues)
                if str_status != QualityStatus.VALID:
                    f_status = str_status

            # Financial validation
            if fname in ("estimated_cost", "awarded_cost"):
                fin_status, fin_issues = FieldValidator.validate_financial(fname, val, estimated_cost=est_cost_val)
                if fin_issues:
                    issues.extend(fin_issues)
                if fin_status != QualityStatus.VALID:
                    f_status = fin_status

            # Geographic validation
            if fname in ("latitude", "longitude", "road_length_km"):
                lat_val = p_data.latitude.value if p_data.latitude else None
                lon_val = p_data.longitude.value if p_data.longitude else None
                len_val = p_data.road_length_km.value if p_data.road_length_km else None
                geo_statuses, geo_issues = FieldValidator.validate_geographic(lat_val, lon_val, len_val)
                if geo_issues:
                    # Append issues relevant to current field
                    issues.extend([i for i in geo_issues if i.field_name == fname])
                if fname in geo_statuses:
                    f_status = geo_statuses[fname]

            # 2. Source Provenance & Freshness Evaluation
            prov_status, is_supp, is_stale, prov_issues = SourceQualityService.evaluate_field_provenance(fname, ev_field)
            if prov_issues:
                issues.extend(prov_issues)
            if not is_supp:
                fields_unsupported += 1
                f_status = QualityStatus.UNSUPPORTED
            if is_stale:
                stale_fields_count += 1

            # 3. Cross-Source Conflict Evaluation
            has_conflict, conf_issues = SourceQualityService.detect_cross_source_conflicts(fname, ev_field)
            if conf_issues:
                issues.extend(conf_issues)
            if has_conflict:
                cross_source_conflicts += 1
                f_status = QualityStatus.SUSPICIOUS

            # Aggregate field counts
            if f_status == QualityStatus.VALID:
                fields_valid += 1
            elif f_status == QualityStatus.SUSPICIOUS:
                fields_suspicious += 1
            elif f_status == QualityStatus.INVALID:
                fields_invalid += 1

            field_reports.append(FieldQualityReport(
                field_name=fname,
                value=val,
                verification_status=ev_field.verification_status.value if hasattr(ev_field.verification_status, "value") else str(ev_field.verification_status),
                quality_status=f_status,
                quality_score=1.0 if f_status == QualityStatus.VALID else (0.5 if f_status == QualityStatus.SUSPICIOUS else 0.0),
                issues=[i for i in issues if i.field_name == fname],
                sources_count=len(ev_field.sources or []),
                is_stale=is_stale
            ))

        # 4. Cross-Field Constraints Validation
        cf_issues = CrossFieldValidator.validate_cross_fields(p_data)
        if cf_issues:
            issues.extend(cf_issues)

        # 5. Duplicate Candidates Detection
        duplicate_candidates = []
        if self.db:
            detector = DuplicateDetector(self.db)
            duplicate_candidates = detector.find_duplicate_candidates(project_name, p_data)

        # 6. Quality Score & Classification Calculation
        has_critical_error = any(i.severity in (QualitySeverity.ERROR, QualitySeverity.CRITICAL) for i in issues)
        is_quarantined = any(
            i.rule_name in (
                "NEGATIVE_COST", "INVALID_LATITUDE_RANGE", "INVALID_LONGITUDE_RANGE",
                "DEADLINE_BEFORE_PUBLICATION", "END_BEFORE_START_DATE", "NEGATIVE_ROAD_LENGTH"
            ) for i in issues
        )

        non_empty = fields_valid + fields_suspicious + fields_invalid
        if non_empty > 0:
            raw_score = (fields_valid + (0.5 * fields_suspicious)) / float(non_empty)
        else:
            raw_score = 0.5

        # Penalty for conflicts and critical errors
        conflict_penalty = cross_source_conflicts * 0.05
        overall_score = max(0.0, round(raw_score - conflict_penalty, 2))

        if is_quarantined or has_critical_error:
            overall_score = min(overall_score, 0.35)

        # Quality Classification
        if is_quarantined:
            quality_class = QualityClass.QUARANTINED
        elif overall_score >= 0.90 and not has_critical_error and fields_invalid == 0:
            quality_class = QualityClass.EXCELLENT
        elif overall_score >= 0.75 and not has_critical_error:
            quality_class = QualityClass.GOOD
        elif overall_score >= 0.60:
            quality_class = QualityClass.FAIR
        elif overall_score >= 0.40:
            quality_class = QualityClass.POOR
        else:
            quality_class = QualityClass.INVALID

        # 7. Merge Eligibility Calculation
        merge_blockers: List[str] = []
        if has_critical_error:
            merge_blockers.append("CRITICAL_VALIDATION_ERRORS")
        if is_quarantined:
            merge_blockers.append("QUARANTINED_RECORD")
        if p_data.tender_id and p_data.tender_id.verification_status == "CONFLICTING":
            merge_blockers.append("CONFLICTING_TENDER_ID")
        if p_data.contractor and p_data.contractor.value and not p_data.contractor.sources:
            merge_blockers.append("UNSUPPORTED_CONTRACTOR")
        if fields_invalid > 0:
            merge_blockers.append(f"{fields_invalid}_INVALID_FIELDS")

        merge_eligible = len(merge_blockers) == 0 and overall_score >= 0.60

        report_response = ResearchQualityReportResponse(
            research_run_id=research_run_id,
            project_name=project_name,
            overall_quality_score=overall_score,
            quality_class=quality_class,
            fields_checked=fields_checked,
            fields_valid=fields_valid,
            fields_suspicious=fields_suspicious,
            fields_invalid=fields_invalid,
            fields_missing=fields_missing,
            fields_unsupported=fields_unsupported,
            cross_source_conflicts=cross_source_conflicts,
            duplicate_candidates_count=len(duplicate_candidates),
            stale_fields_count=stale_fields_count,
            merge_eligible=merge_eligible,
            merge_blockers=merge_blockers,
            is_quarantined=is_quarantined,
            issues=issues,
            evaluated_at=datetime.now(timezone.utc).isoformat()
        )

        # 8. Persist to Database without Canonical Table Mutations
        if self.db and research_run_id:
            try:
                report_model = ResearchQualityReportModel(
                    research_run_id=research_run_id,
                    project_name=project_name,
                    overall_quality_score=overall_score,
                    quality_class=quality_class.value,
                    fields_checked=fields_checked,
                    fields_valid=fields_valid,
                    fields_suspicious=fields_suspicious,
                    fields_invalid=fields_invalid,
                    fields_missing=fields_missing,
                    fields_unsupported=fields_unsupported,
                    cross_source_conflicts=cross_source_conflicts,
                    duplicate_candidates_count=len(duplicate_candidates),
                    stale_fields_count=stale_fields_count,
                    merge_eligible=merge_eligible,
                    merge_blockers=merge_blockers,
                    is_quarantined=is_quarantined
                )
                self.db.add(report_model)
                self.db.flush()

                # Add Issue Models
                for issue in issues:
                    iss_model = ResearchQualityIssueModel(
                        report_id=report_model.id,
                        field_name=issue.field_name,
                        rule_name=issue.rule_name,
                        severity=issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                        description=issue.description,
                        current_value=str(issue.current_value) if issue.current_value is not None else None,
                        source_references=issue.source_references
                    )
                    self.db.add(iss_model)

                # Add Duplicate Models
                for dup in duplicate_candidates:
                    dup_model = ResearchDuplicateCandidateModel(
                        report_id=report_model.id,
                        canonical_project_id=dup.candidate_id,
                        match_score=dup.match_score,
                        matching_signals=dup.matching_signals,
                        conflicting_signals=dup.conflicting_signals
                    )
                    self.db.add(dup_model)

                self.db.commit()
                report_response.id = report_model.id
            except Exception as db_err:
                self.db.rollback()
                logger.warning(f"Error persisting ResearchQualityReportModel: {db_err}")

        return report_response
