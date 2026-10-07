from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.schemas.research import (
    ProjectResearchRequest,
    ProjectResearchResult,
    ResearchStatus
)
from backend.services.research_pipeline import GeminiResearcher
from backend.auth.schemas import UserRole
from backend.auth.models import UserModel
from backend.auth.dependencies import require_role

from fastapi.responses import JSONResponse
from backend.models.research import ResearchRun, ProjectFieldEvidence
from backend.models.data_quality import ResearchQualityReportModel, ResearchQualityIssueModel
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/research", tags=["Research"])

@router.post(
    "/project",
    response_model=ProjectResearchResult,
    summary="Research a project using evidence-based Gemini researcher"
)
def research_project(
    payload: ProjectResearchRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
):
    """
    Submits a project name query to the live evidence-based project research pipeline.
    Discovers sources, extracts verified facts with Gemini, detects conflicts, and persists audit records.
    """
    if not payload.project_name or not payload.project_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_name query cannot be empty"
        )

    researcher = GeminiResearcher()
    result = researcher.research_project(
        project_name=payload.project_name.strip(),
        db=db,
        force_refresh=payload.force_refresh
    )

    return result

@router.get(
    "/{research_run_id}/json",
    summary="Download complete research run result as JSON"
)
def get_research_run_json(
    research_run_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Exports the complete research API response payload as downloadable JSON.
    """
    run = db.query(ResearchRun).filter(ResearchRun.id == research_run_id).first()
    if not run or not run.result_payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ResearchRun with id {research_run_id} not found or has no result payload"
        )

    payload = dict(run.result_payload) if run.result_payload else {}
    
    # Top-level required attributes
    payload["research_run_id"] = run.id
    payload["project_name_query"] = run.query_project_name

    # Evidence list from DB
    ev_models = db.query(ProjectFieldEvidence).filter(ProjectFieldEvidence.research_run_id == run.id).all()
    evidence_list = [
        {
            "field_name": ev.field_name,
            "extracted_value": ev.extracted_value,
            "verification_status": ev.verification_status,
            "confidence": ev.confidence,
            "evidence_snippet": ev.evidence_snippet,
            "source_url": ev.source.source_url if ev.source else None,
            "retrieved_at": ev.retrieved_at.isoformat() if ev.retrieved_at else None
        }
        for ev in ev_models
    ]
    payload["evidence"] = evidence_list

    # Aggregate candidate values across fields
    candidate_values = []
    project_data = payload.get("project", {})
    if isinstance(project_data, dict):
        for field, details in project_data.items():
            if isinstance(details, dict) and "candidate_values" in details and details["candidate_values"]:
                for c in details["candidate_values"]:
                    c_copy = dict(c) if isinstance(c, dict) else c
                    if isinstance(c_copy, dict):
                        c_copy["field_name"] = field
                    candidate_values.append(c_copy)
    payload["candidate_values"] = candidate_values

    # Verification mapping
    payload["verification"] = payload.get("field_verifications", {})

    # Conflicts list
    conflicts = []
    if isinstance(project_data, dict):
        for field, details in project_data.items():
            if isinstance(details, dict) and details.get("verification_status") == "CONFLICTING":
                conflicts.append({
                    "field_name": field,
                    "value": details.get("value"),
                    "sources": details.get("sources", []),
                    "evidence_snippet": details.get("evidence_text")
                })
    payload["conflicts"] = conflicts

    # Quality Report (retrieve from DB or compute)
    quality_report = None
    qr_model = db.query(ResearchQualityReportModel).filter(
        ResearchQualityReportModel.research_run_id == run.id
    ).order_by(ResearchQualityReportModel.created_at.desc()).first()

    if qr_model:
        issues_models = db.query(ResearchQualityIssueModel).filter(
            ResearchQualityIssueModel.report_id == qr_model.id
        ).all()
        quality_report = {
            "report_id": qr_model.id,
            "research_run_id": run.id,
            "project_name": qr_model.project_name,
            "overall_quality_score": qr_model.overall_quality_score,
            "quality_class": qr_model.quality_class,
            "fields_checked": qr_model.fields_checked,
            "fields_valid": qr_model.fields_valid,
            "fields_suspicious": qr_model.fields_suspicious,
            "fields_invalid": qr_model.fields_invalid,
            "fields_missing": qr_model.fields_missing,
            "fields_unsupported": qr_model.fields_unsupported,
            "cross_source_conflicts": qr_model.cross_source_conflicts,
            "stale_fields_count": qr_model.stale_fields_count,
            "duplicate_candidates_count": qr_model.duplicate_candidates_count,
            "quarantined": getattr(qr_model, "is_quarantined", getattr(qr_model, "quarantined", False)),
            "is_quarantined": getattr(qr_model, "is_quarantined", getattr(qr_model, "quarantined", False)),
            "merge_eligible": qr_model.merge_eligible,
            "created_at": qr_model.created_at.isoformat() if qr_model.created_at else None,
            "issues": [
                {
                    "field_name": iss.field_name,
                    "rule_name": iss.rule_name,
                    "severity": iss.severity,
                    "description": iss.description,
                    "current_value": iss.current_value,
                    "source_references": iss.source_references or []
                }
                for iss in issues_models
            ]
        }
    else:
        try:
            from backend.schemas.research import ProjectResearchResult
            from backend.services.data_quality.data_quality_service import DataQualityService
            res_obj = ProjectResearchResult(**run.result_payload)
            dq_service = DataQualityService(db)
            report_res = dq_service.validate_research_result(res_obj, research_run_id=run.id)
            quality_report = report_res.model_dump()
        except Exception:
            quality_report = {}

    payload["quality_report"] = quality_report

    return JSONResponse(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=research_run_{research_run_id}.json"
        }
    )

