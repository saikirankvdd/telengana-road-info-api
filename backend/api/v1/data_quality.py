from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.data_quality import (
    ValidationRequest,
    ResearchQualityReportResponse,
    ValidationIssue
)
from backend.schemas.research import ProjectResearchResult
from backend.models.research import ResearchRun
from backend.models.data_quality import ResearchQualityReportModel, ResearchQualityIssueModel
from backend.services.data_quality.data_quality_service import DataQualityService
from backend.services.research_pipeline import GeminiResearcher
from backend.auth.schemas import UserRole
from backend.auth.models import UserModel
from backend.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/research", tags=["Data Quality & Validation"])


@router.post(
    "/validate",
    response_model=ResearchQualityReportResponse,
    summary="Validate research result quality and completeness"
)
def validate_research(
    payload: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
):
    """
    Evaluates research result against field, cross-field, provenance, conflict, and freshness rules.
    Calculates deterministic quality score, classification, and merge eligibility.
    """
    researcher = GeminiResearcher()

    if payload.research_run_id:
        run = db.query(ResearchRun).filter(ResearchRun.id == payload.research_run_id).first()
        if not run or not run.result_payload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ResearchRun with id {payload.research_run_id} not found"
            )
        res_obj = ProjectResearchResult(**run.result_payload)
        res_obj.project_id = str(run.id)
        run_id = run.id
    elif payload.project_name:
        res_obj = researcher.research_project(
            project_name=payload.project_name.strip(),
            db=db,
            force_refresh=payload.force_refresh
        )
        run_id = int(res_obj.project_id) if res_obj.project_id and res_obj.project_id.isdigit() else None
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either research_run_id or project_name must be provided"
        )

    service = DataQualityService(db)
    report = service.validate_research_result(res_obj, research_run_id=run_id)
    return report


@router.get(
    "/quality/{research_run_id}",
    response_model=ResearchQualityReportResponse,
    summary="Retrieve data quality report for a research run"
)
def get_quality_report(
    research_run_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    r = db.query(ResearchQualityReportModel).filter(
        ResearchQualityReportModel.research_run_id == research_run_id
    ).order_by(ResearchQualityReportModel.created_at.desc()).first()

    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality report for research_run_id {research_run_id} not found"
        )

    issues_models = db.query(ResearchQualityIssueModel).filter(
        ResearchQualityIssueModel.report_id == r.id
    ).all()

    issues = [
        ValidationIssue(
            field_name=iss.field_name,
            rule_name=iss.rule_name,
            severity=iss.severity,
            description=iss.description,
            current_value=iss.current_value,
            source_references=iss.source_references or []
        )
        for iss in issues_models
    ]

    return ResearchQualityReportResponse(
        id=r.id,
        research_run_id=r.research_run_id,
        project_name=r.project_name,
        overall_quality_score=r.overall_quality_score,
        quality_class=r.quality_class,
        fields_checked=r.fields_checked,
        fields_valid=r.fields_valid,
        fields_suspicious=r.fields_suspicious,
        fields_invalid=r.fields_invalid,
        fields_missing=r.fields_missing,
        fields_unsupported=r.fields_unsupported,
        cross_source_conflicts=r.cross_source_conflicts,
        duplicate_candidates_count=r.duplicate_candidates_count,
        stale_fields_count=r.stale_fields_count,
        merge_eligible=r.merge_eligible,
        merge_blockers=r.merge_blockers or [],
        is_quarantined=r.is_quarantined,
        issues=issues,
        evaluated_at=r.created_at.isoformat()
    )


@router.get(
    "/quality/{research_run_id}/issues",
    response_model=List[ValidationIssue],
    summary="Retrieve validation issues for a research run"
)
def get_quality_issues(
    research_run_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    report = db.query(ResearchQualityReportModel).filter(
        ResearchQualityReportModel.research_run_id == research_run_id
    ).order_by(ResearchQualityReportModel.created_at.desc()).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality report for research_run_id {research_run_id} not found"
        )

    issues_models = db.query(ResearchQualityIssueModel).filter(
        ResearchQualityIssueModel.report_id == report.id
    ).all()

    return [
        ValidationIssue(
            field_name=iss.field_name,
            rule_name=iss.rule_name,
            severity=iss.severity,
            description=iss.description,
            current_value=iss.current_value,
            source_references=iss.source_references or []
        )
        for iss in issues_models
    ]


@router.post(
    "/quality/{research_run_id}/revalidate",
    response_model=ResearchQualityReportResponse,
    summary="Re-evaluate data quality using latest validation rules"
)
def revalidate_research(
    research_run_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
):
    run = db.query(ResearchRun).filter(ResearchRun.id == research_run_id).first()
    if not run or not run.result_payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ResearchRun with id {research_run_id} not found or missing payload"
        )

    res_obj = ProjectResearchResult(**run.result_payload)
    res_obj.project_id = str(run.id)

    service = DataQualityService(db)
    report = service.validate_research_result(res_obj, research_run_id=run.id)
    return report
