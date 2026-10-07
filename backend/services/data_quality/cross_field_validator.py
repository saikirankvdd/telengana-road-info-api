import logging
from typing import List, Optional
from datetime import datetime, timezone

from backend.schemas.research import ProjectResearchData
from backend.schemas.data_quality import QualitySeverity, ValidationIssue
from backend.services.data_quality.field_validator import FieldValidator

logger = logging.getLogger(__name__)


class CrossFieldValidator:
    """
    Evaluates complex validation constraints across multiple research fields.
    """

    @staticmethod
    def validate_cross_fields(project_data: ProjectResearchData) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        est_cost = project_data.estimated_cost.value if project_data.estimated_cost else None
        awd_cost = project_data.awarded_cost.value if project_data.awarded_cost else None

        pub_date = project_data.publication_date.value if hasattr(project_data, "publication_date") and project_data.publication_date else None
        sub_deadline = project_data.submission_deadline.value if hasattr(project_data, "submission_deadline") and project_data.submission_deadline else None
        awd_date = project_data.awarded_date.value if hasattr(project_data, "awarded_date") and project_data.awarded_date else None
        start_date = project_data.contract_start_date.value if hasattr(project_data, "contract_start_date") and project_data.contract_start_date else None
        end_date = project_data.contract_end_date.value if hasattr(project_data, "contract_end_date") and project_data.contract_end_date else None
        status = project_data.status.value if project_data.status else None

        # 1. Date Sequence Validation
        date_issues = FieldValidator.validate_date_sequence(
            pub_date_val=pub_date,
            sub_deadline_val=sub_deadline,
            award_date_val=awd_date,
            start_date_val=start_date,
            end_date_val=end_date
        )
        issues.extend(date_issues)

        # 2. Completed Project with Future Contract End Date Check
        if status and str(status).lower() in ("completed", "finished", "commissioned"):
            parsed_end = FieldValidator.parse_date(end_date)
            if parsed_end and parsed_end > datetime.now(timezone.utc).replace(tzinfo=None):
                issues.append(ValidationIssue(
                    field_name="status",
                    rule_name="COMPLETED_WITH_FUTURE_END_DATE",
                    severity=QualitySeverity.WARNING,
                    description=f"Project status is '{status}' but contract_end_date is in the future ({parsed_end.strftime('%Y-%m-%d')})",
                    current_value=status
                ))

        # 3. Awarded cost vs Estimated cost ratio sanity check
        if est_cost is not None and awd_cost is not None:
            try:
                e_val = float(est_cost)
                a_val = float(awd_cost)
                if e_val > 0 and a_val > e_val * 3.0:
                    issues.append(ValidationIssue(
                        field_name="awarded_cost",
                        rule_name="AWARDED_COST_HUGE_VARIANCE",
                        severity=QualitySeverity.WARNING,
                        description=f"Awarded cost (₹{a_val} Cr) is more than 3x the estimated cost (₹{e_val} Cr)",
                        current_value=awd_cost
                    ))
            except (ValueError, TypeError):
                pass

        return issues
