import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.connection import SessionLocal
from backend.models.project import Project
from backend.models.tender import Tender
from backend.models.contract import Contract
from backend.models.contractor import Contractor
from backend.models.research import ResearchRun, ProjectResearchSource, ProjectFieldEvidence
from backend.schemas.research import (
    SourceModel,
    SourceType,
    AuthorityLevel,
    VerificationStatus,
    CandidateValue,
    ResearchStatus
)
from backend.services.search_provider import LiveSearchProvider, categorize_source
from backend.services.source_retriever import LiveSourceRetriever
from backend.services.gemini_extractor import GeminiExtractorService
from backend.services.research_pipeline import GeminiResearcher

client = TestClient(app)
API_KEY_HEADER = {"X-API-Key": "tg_road_intel_secret_key_2026"}

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_source_categorization_and_authority():
    stype, auth = categorize_source("https://tender.telangana.gov.in/notice/101", "Tender Notice")
    assert stype == SourceType.TENDER_PORTAL
    assert auth == AuthorityLevel.PRIMARY

    stype, auth = categorize_source("https://www.thehindu.com/news/national/telangana/uppal-flyover", "Uppal Flyover News")
    assert stype == SourceType.NEWS_MEDIA
    assert auth == AuthorityLevel.SECONDARY

    stype, auth = categorize_source("https://someblog.com/uppal-corridor", "Blog post")
    assert stype == SourceType.OTHER
    assert auth == AuthorityLevel.TERTIARY

def test_search_provider_query_generation():
    provider = LiveSearchProvider()
    queries = provider.generate_queries("Uppal Elevated Corridor")
    assert len(queries) >= 3
    assert any("Uppal Elevated Corridor" in q for q in queries)

def test_live_source_retriever_fallback():
    retriever = LiveSourceRetriever(timeout_seconds=2.0)
    src = SourceModel(
        source_name="Nonexistent Page",
        source_url="https://invalid.domain.telangana.test/page",
        evidence_text="Fallback search snippet text"
    )
    content = retriever.fetch_content(src)
    assert content == "Fallback search snippet text"

def test_test_case_a_uppal_elevated_corridor(db_session: Session):
    """Test Case A: Uppal Elevated Corridor research execution"""
    # Record historical DB counts
    initial_project_count = db_session.query(Project).count()
    initial_tender_count = db_session.query(Tender).count()
    initial_contractor_count = db_session.query(Contractor).count()

    response = client.post(
        "/api/v1/research/project",
        json={"project_name": "Uppal Elevated Corridor", "force_refresh": True},
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()

    assert data["project_name_query"] == "Uppal Elevated Corridor"
    assert data["research_metadata"]["research_status"] == "COMPLETED"
    assert "project" in data

    # Verify database baseline tables remained completely UNCHANGED (mutation count = 0)
    assert db_session.query(Project).count() == initial_project_count
    assert db_session.query(Tender).count() == initial_tender_count
    assert db_session.query(Contractor).count() == initial_contractor_count

    # Verify research audit tables persisted records
    runs = db_session.query(ResearchRun).filter(ResearchRun.query_project_name == "Uppal Elevated Corridor").all()
    assert len(runs) > 0

def test_test_case_b_iit_hyderabad(db_session: Session):
    """Test Case B: IIT Hyderabad campus infrastructure research execution"""
    response = client.post(
        "/api/v1/research/project",
        json={"project_name": "IIT Hyderabad campus infrastructure", "force_refresh": True},
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name_query"] == "IIT Hyderabad campus infrastructure"
    assert data["research_metadata"]["research_status"] == "COMPLETED"

def test_test_case_c_historical_existing_project(db_session: Session):
    """Test Case C: Project that exists in historical database baseline"""
    existing_proj = db_session.query(Project).first()
    proj_name = existing_proj.project_name if existing_proj else "Kalyan-Shilphata Road Project"

    initial_project_count = db_session.query(Project).count()

    response = client.post(
        "/api/v1/research/project",
        json={"project_name": proj_name, "force_refresh": True},
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name_query"] == proj_name

    # Check baseline unchanged
    assert db_session.query(Project).count() == initial_project_count

def test_test_case_d_deliberately_nonexistent_project(db_session: Session):
    """Test Case D: Deliberately nonexistent project query"""
    fake_name = "XYZ_Fake_Nonexistent_Bridge_Project_99999_TG"
    response = client.post(
        "/api/v1/research/project",
        json={"project_name": fake_name, "force_refresh": True},
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name_query"] == fake_name

    # Check that missing fields return NOT_FOUND and value = null (No hallucination)
    project_data = data["project"]
    assert project_data["tender_id"]["value"] is None
    assert project_data["tender_id"]["verification_status"] == "NOT_FOUND"
    assert project_data["government_order_number"]["value"] is None
    assert project_data["government_order_number"]["verification_status"] == "NOT_FOUND"

def test_conflicting_evidence_retention(db_session: Session):
    """Verify that conflicting credible sources preserve CONFLICTING status and candidate values"""
    src1 = SourceModel(
        source_id="src_01",
        source_name="Gov Portal",
        source_url="https://telangana.gov.in/go1",
        source_type=SourceType.GOVERNMENT_ORDER,
        authority_level=AuthorityLevel.PRIMARY,
        evidence_text="GO sanctioning 679.50 Cr"
    )
    src2 = SourceModel(
        source_id="src_02",
        source_name="Gov Portal 2",
        source_url="https://media.com/news1",
        source_type=SourceType.GOVERNMENT_PORTAL,
        authority_level=AuthorityLevel.PRIMARY,
        evidence_text="Cost reported as 750 Cr"
    )

    researcher = GeminiResearcher(
        search_provider=type("MockSearch", (), {"search": lambda self, q, max_total_results=10: [src1, src2]})()
    )

    # Mock extractor returning different values for src1 and src2
    class MockConflictExtractor:
        def extract_evidence(self, project_name, source, raw_content):
            if "go1" in (source.source_url or ""):
                return {"estimated_cost": {"value": 679.50, "evidence_snippet": "679.50 Cr", "confidence": 0.9}}
            else:
                return {"estimated_cost": {"value": 750.00, "evidence_snippet": "750 Cr", "confidence": 0.7}}

    researcher.extractor = MockConflictExtractor()
    result = researcher.research_project("Conflict Test Project", initial_sources=[src1, src2], db=db_session, force_refresh=True, search_adapters=[])

    field = result.project.estimated_cost
    assert field.verification_status == VerificationStatus.CONFLICTING
    assert field.value is None
    assert len(field.candidate_values) == 2
    assert len(field.sources) == 2

def test_gemini_failure_handling(db_session: Session):
    """Verify graceful handling when Gemini client fails or throws exception"""
    researcher = GeminiResearcher()

    class FailingExtractor:
        def extract_evidence(self, project_name, source, raw_content):
            raise RuntimeError("Gemini API Rate Limit 429")

    researcher.extractor = FailingExtractor()
    src = SourceModel(source_name="Sample Source", evidence_text="Sample text")
    
    # Should not crash, but return NOT_FOUND safely
    result = researcher.research_project("Failing Test Project", initial_sources=[src], db=None, force_refresh=True)
    assert result.research_metadata.research_status == ResearchStatus.COMPLETED
    assert result.project.tender_id.verification_status == VerificationStatus.NOT_FOUND
