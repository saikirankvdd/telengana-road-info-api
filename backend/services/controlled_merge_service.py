import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.schemas.research_merge import (
    ReviewDecisionRequest,
    MergeExecutionRequest,
    ReviewStatus,
    FieldDecision,
    MergeActionType
)
from backend.models.project import Project, ProjectContractor, ProjectTender, ProjectAuthority
from backend.models.tender import Tender
from backend.models.contractor import Contractor
from backend.models.authority import Authority
from backend.models.project_location import ProjectLocation
from backend.models.research import ResearchRun, ProjectFieldEvidence
from backend.models.research_merge import ResearchMergeReview, ResearchMergeAction

logger = logging.getLogger(__name__)

class ControlledMergeService:
    def __init__(self, db: Session):
        self.db = db

    def update_review(
        self,
        review_id: int,
        req: ReviewDecisionRequest
    ) -> ResearchMergeReview:
        review = self.db.query(ResearchMergeReview).filter(ResearchMergeReview.id == review_id).first()
        if not review:
            raise ValueError(f"ResearchMergeReview with id {review_id} not found")

        # Update field decisions
        current_decisions = dict(review.field_decisions or {})
        for field, decision in req.field_decisions.items():
            current_decisions[field] = decision.value if hasattr(decision, "value") else str(decision)
        review.field_decisions = current_decisions
        flag_modified(review, "field_decisions")

        # Determine overall status
        if req.overall_status:
            review.review_status = req.overall_status.value if hasattr(req.overall_status, "value") else str(req.overall_status)
        else:
            # If any decision is APPROVE, overall status becomes APPROVED
            if any(v == FieldDecision.APPROVE.value for v in current_decisions.values()):
                review.review_status = ReviewStatus.APPROVED.value
            elif any(v == FieldDecision.NEEDS_MORE_EVIDENCE.value for v in current_decisions.values()):
                review.review_status = ReviewStatus.NEEDS_MORE_EVIDENCE.value

        review.reviewed_by = req.reviewed_by
        review.reviewed_at = datetime.now(timezone.utc)
        if req.review_notes:
            review.review_notes = req.review_notes

        self.db.commit()
        return review

    def execute_merge(
        self,
        review_id: int,
        approved_by: str = "admin",
        notes: Optional[str] = None
    ) -> List[ResearchMergeAction]:
        review = self.db.query(ResearchMergeReview).filter(ResearchMergeReview.id == review_id).first()
        if not review:
            raise ValueError(f"ResearchMergeReview with id {review_id} not found")

        if review.review_status not in (ReviewStatus.APPROVED.value, ReviewStatus.PENDING.value, ReviewStatus.NEEDS_MORE_EVIDENCE.value, ReviewStatus.REJECTED.value):
            raise ValueError(f"Cannot merge review in status '{review.review_status}'")

        decisions = review.field_decisions or {}
        field_comp = review.field_comparison or {}

        # Collect fields with explicit APPROVE decision
        approved_fields = {f: details for f, details in field_comp.items() if decisions.get(f) == FieldDecision.APPROVE.value}

        if not approved_fields and review.review_status == ReviewStatus.APPROVED.value:
            # If review status is APPROVED overall, treat all non-conflicting proposed fields as approved
            approved_fields = {
                f: details for f, details in field_comp.items()
                if details.get("comparison_result") in ("PROPOSED_INSERT", "PROPOSED_UPDATE", "MATCHED")
                and details.get("research_value") is not None
            }

        actions: List[ResearchMergeAction] = []

        try:
            # Begin explicit transaction
            with self.db.begin_nested():
                target_project: Optional[Project] = None

                if review.candidate_entity_id:
                    target_project = self.db.query(Project).filter(Project.id == review.candidate_entity_id).first()

                # If entity is NEW_ENTITY and approved fields exist, create a new canonical Project entity
                if not target_project:
                    p_name_detail = approved_fields.get("project_name") or field_comp.get("project_name", {})
                    p_name = p_name_detail.get("research_value") or review.research_run.query_project_name
                    
                    target_project = Project(
                        project_id=f"PRJ_CANONICAL_{review.id:04d}",
                        project_name=p_name,
                        normalized_project_name=p_name.lower().strip()
                    )
                    self.db.add(target_project)
                    self.db.flush()

                    review.candidate_entity_id = target_project.id

                # Iterate through all field comparisons
                for field_name, details in field_comp.items():
                    decision = decisions.get(field_name, FieldDecision.PENDING.value)
                    res_val = details.get("research_value")
                    can_val = details.get("canonical_value")

                    # RULE: NOT_FOUND or NULL research value MUST NEVER replace canonical value
                    if res_val is None or details.get("verification_status") == "NOT_FOUND":
                        action_type = MergeActionType.NO_CHANGE
                        act = ResearchMergeAction(
                            review_id=review.id,
                            research_run_id=review.research_run_id,
                            field_name=field_name,
                            target_table="projects",
                            target_record_id=target_project.id,
                            previous_value=str(can_val) if can_val is not None else None,
                            new_value=None,
                            action=action_type.value,
                            approved_by=approved_by,
                            approved_at=datetime.now(timezone.utc)
                        )
                        self.db.add(act)
                        actions.append(act)
                        continue

                    # Handle REJECT or NEEDS_MORE_EVIDENCE
                    if decision in (FieldDecision.REJECT.value, FieldDecision.NEEDS_MORE_EVIDENCE.value):
                        act = ResearchMergeAction(
                            review_id=review.id,
                            research_run_id=review.research_run_id,
                            field_name=field_name,
                            target_table="projects",
                            target_record_id=target_project.id,
                            previous_value=str(can_val) if can_val is not None else None,
                            new_value=str(res_val),
                            action=MergeActionType.REJECT.value,
                            approved_by=approved_by,
                            approved_at=datetime.now(timezone.utc)
                        )
                        self.db.add(act)
                        actions.append(act)
                        continue

                    # Handle APPROVE decision
                    if decision == FieldDecision.APPROVE.value or field_name in approved_fields:
                        action_type = MergeActionType.INSERT if can_val is None else MergeActionType.UPDATE
                        prev_val_str = str(can_val) if can_val is not None else None
                        new_val_str = str(res_val)

                        # Apply value update to canonical target_project or relationships
                        self.apply_field_to_canonical(target_project, field_name, res_val)

                        # Look up field evidence ID if available
                        ev_record = self.db.query(ProjectFieldEvidence).filter(
                            ProjectFieldEvidence.research_run_id == review.research_run_id,
                            ProjectFieldEvidence.field_name == field_name
                        ).first()

                        act = ResearchMergeAction(
                            review_id=review.id,
                            research_run_id=review.research_run_id,
                            field_name=field_name,
                            target_table=self.get_target_table_for_field(field_name),
                            target_record_id=target_project.id,
                            previous_value=prev_val_str,
                            new_value=new_val_str,
                            source_evidence_id=ev_record.id if ev_record else None,
                            action=action_type.value,
                            approved_by=approved_by,
                            approved_at=datetime.now(timezone.utc)
                        )
                        self.db.add(act)
                        actions.append(act)

                review.review_status = ReviewStatus.APPROVED.value
                review.reviewed_by = approved_by
                review.reviewed_at = datetime.now(timezone.utc)
                if notes:
                    review.review_notes = notes

            self.db.commit()
            return actions

        except Exception as e:
            self.db.rollback()
            logger.error(f"Merge execution transaction failed: {e}")
            raise e

    def get_target_table_for_field(self, field_name: str) -> str:
        if field_name in ("district", "constituency", "location", "latitude", "longitude"):
            return "project_locations"
        elif field_name in ("tender_id", "reference_number", "tender_publication_date", "tender_closing_date"):
            return "tenders"
        elif field_name in ("contractor", "contractor_registration"):
            return "contractors"
        elif field_name in ("authority", "department"):
            return "authorities"
        return "projects"

    def apply_field_to_canonical(self, project: Project, field_name: str, value: Any):
        """Safely mutates canonical entity attributes."""
        if field_name == "estimated_cost":
            project.estimated_cost = float(value)
        elif field_name == "awarded_cost":
            project.awarded_cost = float(value)
        elif field_name == "project_length":
            project.length_km = float(value)
        elif field_name == "status":
            project.status = str(value)
        elif field_name == "project_name":
            project.project_name = str(value)
            project.normalized_project_name = str(value).lower().strip()
        elif field_name == "contractor":
            # Link or create Contractor canonical entity
            c_name = str(value).strip()
            contractor = self.db.query(Contractor).filter(Contractor.legal_name == c_name).first()
            if not contractor:
                contractor = Contractor(legal_name=c_name)
                self.db.add(contractor)
                self.db.flush()

            
            p_contractor = self.db.query(ProjectContractor).filter(
                ProjectContractor.project_id == project.id,
                ProjectContractor.contractor_id == contractor.id
            ).first()
            if not p_contractor:
                p_contractor = ProjectContractor(project_id=project.id, contractor_id=contractor.id, role="MAIN_CONTRACTOR")
                self.db.add(p_contractor)

        elif field_name in ("district", "locality", "location", "latitude", "longitude"):
            loc = self.db.query(ProjectLocation).filter(ProjectLocation.project_id == project.id).first()
            if not loc:
                loc = ProjectLocation(project_id=project.id)
                self.db.add(loc)
            
            if field_name == "district":
                loc.district = str(value)
            elif field_name in ("location", "locality"):
                loc.locality = str(value)
            elif field_name == "latitude":
                loc.latitude = float(value)
            elif field_name == "longitude":
                loc.longitude = float(value)
