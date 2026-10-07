import os
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.connection import SessionLocal
from backend.models.research import ResearchRun
from backend.models.project import Project
from backend.models.data_quality import ResearchQualityReportModel
from backend.schemas.research import ProjectResearchResult, ProjectResearchData, ResearchMetadata, SourceModel, EvidentiaryField, VerificationStatus
from backend.auth.models import UserModel
from backend.auth.schemas import UserRole
from backend.auth.service import AuthService

client = TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def auth_headers(db: Session):
    admin = db.query(UserModel).filter(UserModel.role == UserRole.ADMIN.value).first()
    if not admin:
        admin = UserModel(
            username="test_task8_admin",
            email="test_task8_admin@telangana.gov.in",
            password_hash=AuthService.hash_password("AdminPass123!"),
            role=UserRole.ADMIN.value,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = AuthService.create_access_token(data={"sub": admin.username, "role": admin.role})
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": "tg_road_intel_secret_key_2026",
        "Content-Type": "application/json"
    }

def test_json_endpoint_exists_and_handles_invalid_id(auth_headers):
    # 1. Invalid research_run_id returns 404
    res = client.get("/api/v1/research/9999999/json", headers=auth_headers)
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()

def test_json_report_generation_download_and_schema(db, auth_headers):
    # Create mock research run in DB
    dummy_result = ProjectResearchResult(
        project_id="123",
        project_name_query="Uppal Elevated Corridor Test",
        project=ProjectResearchData(
            estimated_cost=EvidentiaryField[float](
                value=626.76,
                verification_status=VerificationStatus.VERIFIED,
                confidence=0.95,
                sources=[SourceModel(source_name="HMDA", source_url="https://hmda.gov.in/pdf", authority_level="PRIMARY")],
                evidence_text="Uppal Elevated Corridor estimated cost INR 626.76 Cr."
            )
        ),
        sources=[SourceModel(source_name="HMDA Portal", source_url="https://hmda.gov.in", authority_level="PRIMARY")],
        field_verifications={"estimated_cost": VerificationStatus.VERIFIED},
        research_metadata=ResearchMetadata(
            sources_checked=5,
            sources_accessed=4,
            fields_found=1,
            fields_verified=1
        )
    )

    run = ResearchRun(
        query_project_name="Uppal Elevated Corridor Test",
        status="COMPLETED",
        duration_seconds=2.5,
        result_payload=dummy_result.model_dump()
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 2. Call GET /api/v1/research/{id}/json
    res = client.get(f"/api/v1/research/{run.id}/json", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/json"
    assert "attachment" in res.headers.get("content-disposition", "")

    data = res.json()

    # 3-9. Verify top-level structure and preserved keys
    assert data["research_run_id"] == run.id
    assert data["project_name_query"] == "Uppal Elevated Corridor Test"
    assert "project" in data
    assert "sources" in data
    assert "evidence" in data
    assert "verification" in data
    assert "quality_report" in data
    assert "research_metadata" in data

    # 10. Populated field has evidence
    cost_field = data["project"].get("estimated_cost", {})
    assert cost_field.get("value") == 626.76
    assert cost_field.get("verification_status") == "VERIFIED"
    assert len(cost_field.get("sources", [])) > 0

    # 11. Unpopulated field remains null
    tender_field = data["project"].get("tender_id", {})
    assert tender_field.get("value") is None
    assert tender_field.get("verification_status") == "NOT_FOUND"

def test_fake_project_anti_hallucination_json_schema(db, auth_headers):
    fake_result = ProjectResearchResult(
        project_id="124",
        project_name_query="XYZ_Fake_Nonexistent_Bridge_Project_99999_TG",
        project=ProjectResearchData(),
        sources=[],
        field_verifications={},
        research_metadata=ResearchMetadata(
            fields_found=0,
            fields_not_found=60
        )
    )
    run = ResearchRun(
        query_project_name="XYZ_Fake_Nonexistent_Bridge_Project_99999_TG",
        status="COMPLETED",
        duration_seconds=1.0,
        result_payload=fake_result.model_dump()
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    res = client.get(f"/api/v1/research/{run.id}/json", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    # 12. Fake project does not hallucinate
    prj = data.get("project", {})
    for k, v in prj.items():
        assert v.get("value") is None
        assert v.get("verification_status") == "NOT_FOUND"

def test_canonical_db_safety_on_report_download(db, auth_headers):
    # 14. Canonical database tables count remains unaffected
    p_count_before = db.query(Project).count()

    dummy_result = ProjectResearchResult(
        project_id="125",
        project_name_query="DB Safety Test Project",
        project=ProjectResearchData()
    )
    run = ResearchRun(
        query_project_name="DB Safety Test Project",
        status="COMPLETED",
        result_payload=dummy_result.model_dump()
    )
    db.add(run)
    db.commit()

    res = client.get(f"/api/v1/research/{run.id}/json", headers=auth_headers)
    assert res.status_code == 200

    p_count_after = db.query(Project).count()
    assert p_count_before == p_count_after
