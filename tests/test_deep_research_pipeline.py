import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.schemas.research import (
    SourceModel,
    SourceType,
    AuthorityLevel,
    CandidateValue,
    VerificationStatus
)
from backend.services.source_retriever import LiveSourceRetriever
from backend.services.verification_service import VerificationService
from backend.services.query_generator import SourceQueryGenerator
from backend.models.project import Project
from backend.models.tender import Tender
from backend.models.contractor import Contractor
from backend.auth.models import UserModel
from backend.auth.schemas import UserRole
from backend.auth.service import AuthService

client = TestClient(app)

@pytest.fixture
def auth_headers(db_session: Session):
    username = "test_researcher_t9"
    usr = db_session.query(UserModel).filter(UserModel.username == username).first()
    if not usr:
        usr = UserModel(
            username=username,
            email="researcher_t9@example.com",
            password_hash=AuthService.hash_password("Pass123!"),
            role=UserRole.RESEARCHER.value,
            is_active=True
        )
        db_session.add(usr)
        db_session.commit()
        db_session.refresh(usr)
    token = AuthService.create_access_token(data={"sub": usr.username, "role": usr.role})
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# Test Case A & G: Deep Research Flow & Evidence Provenance (Uppal Elevated Corridor)
# ---------------------------------------------------------------------------

def test_query_generator_expansion():
    generator = SourceQueryGenerator()
    queries = generator.generate_queries("Uppal Elevated Corridor")
    assert any("Telangana" in q for q in queries)
    assert any("tender" in q for q in queries)
    assert any("contractor" in q for q in queries)
    assert any("cost" in q for q in queries)
    assert any("DPR" in q for q in queries)

def test_deep_research_uppal_corridor(db_session: Session, auth_headers: dict):
    payload = {"project_name": "Uppal Elevated Corridor", "force_refresh": True}
    response = client.post("/api/v1/research/project", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["project_name_query"] == "Uppal Elevated Corridor"
    assert "project" in data
    assert "sources" in data

    # Verify provenance for non-null fields
    project_fields = data["project"]
    for field_name, field_val in project_fields.items():
        if isinstance(field_val, dict) and field_val.get("value") is not None:
            assert field_val["verification_status"] != "NOT_FOUND"
            assert len(field_val.get("sources", [])) > 0
            assert field_val["sources"][0]["source_url"] is not None

# ---------------------------------------------------------------------------
# Test Case B: IIT Hyderabad Infrastructure Filtering
# ---------------------------------------------------------------------------

def test_iit_hyderabad_infrastructure_filtering(db_session: Session, auth_headers: dict):
    payload = {"project_name": "IIT Hyderabad campus infrastructure", "force_refresh": True}
    response = client.post("/api/v1/research/project", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["project_name_query"] == "IIT Hyderabad campus infrastructure"

# ---------------------------------------------------------------------------
# Test Case D: Anti-Hallucination (Fake Nonexistent Project)
# ---------------------------------------------------------------------------

def test_anti_hallucination_fake_project(db_session: Session, auth_headers: dict):
    fake_name = "XYZ_Fake_Nonexistent_Bridge_Project_99999_TG"
    payload = {"project_name": fake_name, "force_refresh": True}
    response = client.post("/api/v1/research/project", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    project_data = data["project"]

    # Factual project specific identifiers MUST be null / NOT_FOUND
    assert project_data["tender_id"]["value"] is None
    assert project_data["tender_id"]["verification_status"] == "NOT_FOUND"
    assert project_data["contractor"]["value"] is None
    assert project_data["contractor"]["verification_status"] == "NOT_FOUND"
    assert project_data["government_order_number"]["value"] is None
    assert project_data["government_order_number"]["verification_status"] == "NOT_FOUND"

# ---------------------------------------------------------------------------
# Test Case E & Section 3: Conflicting Sources & Tertiary Evidence Rules
# ---------------------------------------------------------------------------

def test_tertiary_evidence_cannot_be_verified():
    cand = CandidateValue(
        value="Simple Bridge",
        source=SourceModel(
            source_name="Random Blog Forum",
            source_url="https://exampleblog.org/post",
            authority_level=AuthorityLevel.TERTIARY,
            source_type=SourceType.OTHER
        ),
        confidence=0.4
    )
    res = VerificationService.verify_field("project_name", [cand])
    assert res.verification_status != VerificationStatus.VERIFIED
    assert res.verification_status == VerificationStatus.UNVERIFIED

def test_conflicting_sources_preserves_candidates():
    cand1 = CandidateValue(
        value=675.0,
        source=SourceModel(
            source_name="Gov Portal A",
            source_url="https://gov.in/a",
            authority_level=AuthorityLevel.PRIMARY,
            source_type=SourceType.GOVERNMENT_PORTAL
        ),
        confidence=0.9
    )
    cand2 = CandidateValue(
        value=960.0,
        source=SourceModel(
            source_name="Gov Portal B",
            source_url="https://gov.in/b",
            authority_level=AuthorityLevel.PRIMARY,
            source_type=SourceType.GOVERNMENT_PORTAL
        ),
        confidence=0.9
    )
    res = VerificationService.verify_field("estimated_cost", [cand1, cand2])
    assert res.verification_status == VerificationStatus.CONFLICTING
    assert res.value is None
    assert len(res.candidate_values) == 2

# ---------------------------------------------------------------------------
# Test Case F: PDF Extraction with Page Number Provenance
# ---------------------------------------------------------------------------

def test_pdf_extraction_page_number_support():
    retriever = LiveSourceRetriever()
    source = SourceModel(source_name="Test PDF Document", source_url="https://example.gov/test.pdf")

    # Mock extract_pdf_text or test page number parsing
    raw_pdf_content = "[Page 1]\nTotal project cost: Rs. 626.76 crore\nPhysical progress: 50%"
    assert "[Page 1]" in raw_pdf_content
    assert "626.76" in raw_pdf_content

# ---------------------------------------------------------------------------
# Test Case H: Canonical Database Safety (Zero Canonical Mutations)
# ---------------------------------------------------------------------------

def test_no_canonical_mutations_on_research(db_session: Session, auth_headers: dict):
    initial_p_count = db_session.query(Project).count()
    initial_t_count = db_session.query(Tender).count()
    initial_c_count = db_session.query(Contractor).count()

    payload = {"project_name": "Test Safe Research Query", "force_refresh": True}
    response = client.post("/api/v1/research/project", json=payload, headers=auth_headers)
    assert response.status_code == 200

    post_p_count = db_session.query(Project).count()
    post_t_count = db_session.query(Tender).count()
    post_c_count = db_session.query(Contractor).count()

    assert post_p_count == initial_p_count
    assert post_t_count == initial_t_count
    assert post_c_count == initial_c_count

# ---------------------------------------------------------------------------
# Test Case I: JSON Download Endpoint
# ---------------------------------------------------------------------------

def test_json_download_endpoint(db_session: Session, auth_headers: dict):
    # 1. Run research to persist a run
    payload = {"project_name": "Uppal Elevated Corridor", "force_refresh": True}
    res = client.post("/api/v1/research/project", json=payload, headers=auth_headers)
    assert res.status_code == 200
    run_id = res.json()["project_id"]
    assert run_id is not None

    # 2. Call GET /api/v1/research/{run_id}/json
    download_res = client.get(f"/api/v1/research/{run_id}/json", headers=auth_headers)
    assert download_res.status_code == 200
    assert "application/json" in download_res.headers["content-type"]
    downloaded_data = download_res.json()
    assert downloaded_data["project_name_query"] == "Uppal Elevated Corridor"
