from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.core.security import verify_api_key, verify_admin_key
from backend.schemas.research_merge import (
    ResolveEntityRequest,
    EntityResolutionResult,
    ReviewDecisionRequest,
    MergeExecutionRequest,
    ResearchMergeReviewResponse,
    ResearchMergeActionResponse,
    ReviewStatus
)
from backend.services.entity_resolution_service import EntityResolutionService
from backend.services.controlled_merge_service import ControlledMergeService
from backend.services.research_pipeline import GeminiResearcher
from backend.models.research import ResearchRun, ProjectFieldEvidence
from backend.models.research_merge import ResearchMergeReview, ResearchMergeAction
from backend.models.project import Project
from backend.models.data_quality import ResearchQualityReportModel
from backend.auth.schemas import UserRole
from backend.auth.models import UserModel
from backend.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/research", tags=["Research & Entity Resolution"])

@router.post(
    "/resolve",
    response_model=EntityResolutionResult,
    summary="Resolve research result against canonical database entities"
)
def resolve_entity(
    payload: ResolveEntityRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER, UserRole.REVIEWER]))
):
    """
    Evaluates research result against canonical database entities using 13 deterministic signals.
    Calculates match confidence, compares fields, and creates a pending ResearchMergeReview record.
    """
    researcher = GeminiResearcher()

    if payload.research_run_id:
        run = db.query(ResearchRun).filter(ResearchRun.id == payload.research_run_id).first()
        if not run or not run.result_payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchRun with id {payload.research_run_id} not found or missing payload"
            )
        from backend.schemas.research import ProjectResearchResult
        res_obj = ProjectResearchResult(**run.result_payload)
        res_obj.project_id = str(run.id)
    elif payload.project_name:
        res_obj = researcher.research_project(project_name=payload.project_name.strip(), db=db, force_refresh=payload.force_refresh)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either research_run_id or project_name must be provided"
        )

    resolver = EntityResolutionService(db)
    resolution = resolver.resolve(research_result=res_obj, research_run_id=int(res_obj.project_id) if res_obj.project_id and res_obj.project_id.isdigit() else None)
    
    return resolution


@router.get(
    "/reviews",
    response_model=List[ResearchMergeReviewResponse],
    summary="List research merge review queue"
)
def list_merge_reviews(
    review_status: Optional[str] = None,
    match_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = db.query(ResearchMergeReview)
    if review_status:
        query = query.filter(ResearchMergeReview.review_status == review_status)
    if match_status:
        query = query.filter(ResearchMergeReview.match_status == match_status)

    reviews = query.order_by(ResearchMergeReview.created_at.desc()).all()
    results = []
    for r in reviews:
        results.append(
            ResearchMergeReviewResponse(
                id=r.id,
                research_run_id=r.research_run_id,
                candidate_entity_type=r.candidate_entity_type,
                candidate_entity_id=r.candidate_entity_id,
                match_status=r.match_status,
                match_confidence=r.match_confidence,
                matching_signals=r.matching_signals or [],
                negative_signals=r.negative_signals or [],
                field_comparison=r.field_comparison or {},
                field_decisions=r.field_decisions or {},
                review_status=r.review_status,
                reviewed_by=r.reviewed_by,
                reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
                review_notes=r.review_notes,
                created_at=r.created_at.isoformat()
            )
        )
    return results


@router.get(
    "/reviews/{review_id}",
    response_model=ResearchMergeReviewResponse,
    summary="Get details of a specific merge review record"
)
def get_merge_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    r = db.query(ResearchMergeReview).filter(ResearchMergeReview.id == review_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Review with id {review_id} not found")

    return ResearchMergeReviewResponse(
        id=r.id,
        research_run_id=r.research_run_id,
        candidate_entity_type=r.candidate_entity_type,
        candidate_entity_id=r.candidate_entity_id,
        match_status=r.match_status,
        match_confidence=r.match_confidence,
        matching_signals=r.matching_signals or [],
        negative_signals=r.negative_signals or [],
        field_comparison=r.field_comparison or {},
        field_decisions=r.field_decisions or {},
        review_status=r.review_status,
        reviewed_by=r.reviewed_by,
        reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
        review_notes=r.review_notes,
        created_at=r.created_at.isoformat()
    )


@router.post(
    "/reviews/{review_id}/approve",
    response_model=ResearchMergeReviewResponse,
    summary="Approve review decisions at field or entity level"
)
def approve_review(
    review_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.REVIEWER]))
):
    service = ControlledMergeService(db)
    try:
        payload.overall_status = ReviewStatus.APPROVED
        updated = service.update_review(review_id, payload)
        return get_merge_review(review_id, db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/reviews/{review_id}/reject",
    response_model=ResearchMergeReviewResponse,
    summary="Reject research merge review"
)
def reject_review(
    review_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.REVIEWER]))
):
    service = ControlledMergeService(db)
    try:
        payload.overall_status = ReviewStatus.REJECTED
        service.update_review(review_id, payload)
        return get_merge_review(review_id, db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/reviews/{review_id}/needs-more-evidence",
    response_model=ResearchMergeReviewResponse,
    summary="Mark merge review as needing more evidence"
)
def needs_more_evidence(
    review_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.REVIEWER]))
):
    service = ControlledMergeService(db)
    try:
        payload.overall_status = ReviewStatus.NEEDS_MORE_EVIDENCE
        service.update_review(review_id, payload)
        return get_merge_review(review_id, db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/reviews/{review_id}/needs-more-research",
    response_model=ResearchMergeReviewResponse,
    summary="Mark merge review as needing more research"
)
def needs_more_research(
    review_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.REVIEWER]))
):
    return needs_more_evidence(review_id, payload, db, current_user)


@router.post(
    "/reviews/{review_id}/merge",
    response_model=List[ResearchMergeActionResponse],
    summary="Execute controlled transaction merge into canonical database (Admin Restricted)"
)
def execute_controlled_merge(
    review_id: int,
    payload: MergeExecutionRequest = MergeExecutionRequest(),
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(require_role([UserRole.ADMIN]))
):
    """
    Executes controlled transactional merge of explicitly approved fields into canonical database tables.
    Requires Admin authorization, APPROVED review status, and passing Task 6 quality validation.
    """
    r = db.query(ResearchMergeReview).filter(ResearchMergeReview.id == review_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Review with id {review_id} not found")
    if r.review_status != ReviewStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute merge for review '{review_id}'. Review status must be APPROVED (current status: '{r.review_status}')."
        )

    # Task 6 Quality & Quarantine Validation Safety Check
    if r.research_run_id:
        q_report = db.query(ResearchQualityReportModel).filter(
            ResearchQualityReportModel.research_run_id == r.research_run_id
        ).first()
        if q_report:
            if q_report.is_quarantined:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot merge review '{review_id}'. Research record is QUARANTINED due to severe data validation errors."
                )
            if not q_report.merge_eligible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot merge review '{review_id}'. Research record is not merge eligible. Blockers: {q_report.merge_blockers}"
                )

    service = ControlledMergeService(db)
    try:
        actions = service.execute_merge(
            review_id=review_id,
            approved_by=payload.approved_by or admin_user.username,
            notes=payload.review_notes
        )
        return [
            ResearchMergeActionResponse(
                id=a.id,
                review_id=a.review_id,
                research_run_id=a.research_run_id,
                field_name=a.field_name,
                target_table=a.target_table,
                target_record_id=a.target_record_id,
                previous_value=a.previous_value,
                new_value=a.new_value,
                action=a.action,
                approved_by=a.approved_by,
                approved_at=a.approved_at.isoformat()
            )
            for a in actions
        ]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



@router.get(
    "/projects/{project_id}/evidence",
    summary="Get complete evidence lineage trace for a canonical project"
)
def get_project_evidence_lineage(
    project_id: int,
    db: Session = Depends(get_db)
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Canonical project with id {project_id} not found")

    reviews = db.query(ResearchMergeReview).filter(ResearchMergeReview.candidate_entity_id == project_id).all()
    review_ids = [r.id for r in reviews]
    actions = db.query(ResearchMergeAction).filter(ResearchMergeAction.review_id.in_(review_ids)).all() if review_ids else []

    return {
        "project_id": proj.id,
        "canonical_project_id": proj.project_id,
        "project_name": proj.project_name,
        "merge_reviews_count": len(reviews),
        "merge_actions": [
            {
                "field_name": a.field_name,
                "target_table": a.target_table,
                "previous_value": a.previous_value,
                "new_value": a.new_value,
                "action": a.action,
                "approved_by": a.approved_by,
                "approved_at": a.approved_at.isoformat()
            }
            for a in actions
        ]
    }
