import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.schemas.research import (
    ProjectResearchRequest,
    ProjectResearchResult,
    ProjectResearchData,
    EvidentiaryField,
    SourceModel,
    CandidateValue,
    VerificationStatus,
    SourceType,
    AuthorityLevel,
    ResearchStatus
)
from backend.services.verification_service import VerificationService
from backend.services.gemini_extractor import GeminiExtractorService, RawExtractedField
from backend.services.research_pipeline import GeminiResearcher

client = TestClient(app)
API_KEY_HEADER = {"X-API-Key": "tg_road_intel_secret_key_2026"}

def test_pydantic_validation_defaults():
    data = ProjectResearchData()
    # Test default missing fields behavior
    assert data.tender_id.value is None
    assert data.tender_id.verification_status == VerificationStatus.NOT_FOUND
    assert data.tender_id.confidence == 0.0
    assert data.tender_id.sources == []
    assert data.estimated_cost.value is None
    assert data.estimated_cost.verification_status == VerificationStatus.NOT_FOUND

def test_evidence_object_creation():
    src = SourceModel(
        source_id="src_001",
        source_url="https://tender.telangana.gov.in/notice/101",
        source_name="Telangana eProcurement Portal",
        source_type=SourceType.TENDER_PORTAL,
        publisher="Telangana R&B Department",
        title="Tender Notice for Uppal Corridor",
        evidence_text="Tender ID: TG-RB-2024-8841",
        authority_level=AuthorityLevel.PRIMARY
    )
    assert src.authority_level == AuthorityLevel.PRIMARY
    assert src.source_type == SourceType.TENDER_PORTAL
    assert src.source_id == "src_001"

def test_missing_data_never_fabricated():
    """Test that missing data is marked NOT_FOUND and value is None (MISSING DATA != FABRICATED DATA)"""
    candidates = []  # No evidence provided
    result = VerificationService.verify_field("tender_id", candidates)
    assert result.value is None
    assert result.verification_status == VerificationStatus.NOT_FOUND
    assert result.confidence == 0.0
    assert result.verification_status != VerificationStatus.VERIFIED

def test_single_primary_source_verification():
    src = SourceModel(
        source_id="gov_order_1",
        source_url="https://go.telangana.gov.in/GO_123.pdf",
        source_name="Telangana Gazette / GO Portal",
        source_type=SourceType.GOVERNMENT_ORDER,
        authority_level=AuthorityLevel.PRIMARY,
        evidence_text="GO Ms No 42 sanctioning Rs 679.50 Cr for Uppal Elevated Corridor"
    )
    cand = CandidateValue(
        value=679.50,
        source=src,
        confidence=0.9,
        evidence_snippet="GO Ms No 42 sanctioning Rs 679.50 Cr"
    )
    result = VerificationService.verify_field("estimated_cost", [cand])
    assert result.value == 679.50
    assert result.verification_status == VerificationStatus.VERIFIED
    assert result.confidence >= 0.8

def test_unverified_secondary_source():
    """Test UNVERIFIED state when only a news/media source provides data (UNVERIFIED DATA != VERIFIED DATA)"""
    src = SourceModel(
        source_name="Local News Article",
        source_type=SourceType.NEWS_MEDIA,
        authority_level=AuthorityLevel.TERTIARY,
        evidence_text="Reports claim contractor XYZ won bid"
    )
    cand = CandidateValue(
        value="XYZ Infra Ltd",
        source=src,
        confidence=0.5
    )
    result = VerificationService.verify_field("contractor", [cand])
    assert result.value == "XYZ Infra Ltd"
    assert result.verification_status == VerificationStatus.UNVERIFIED
    assert result.verification_status != VerificationStatus.VERIFIED

def test_multiple_agreeing_sources():
    src1 = SourceModel(
        source_name="eProcurement Portal",
        source_type=SourceType.TENDER_PORTAL,
        authority_level=AuthorityLevel.PRIMARY
    )
    src2 = SourceModel(
        source_name="R&B Department Annual Report",
        source_type=SourceType.GOVERNMENT_DOCUMENT,
        authority_level=AuthorityLevel.PRIMARY
    )
    c1 = CandidateValue(value="TG-RB-2024-8841", source=src1)
    c2 = CandidateValue(value="TG-RB-2024-8841", source=src2)

    result = VerificationService.verify_field("tender_id", [c1, c2])
    assert result.value == "TG-RB-2024-8841"
    assert result.verification_status == VerificationStatus.VERIFIED
    assert len(result.sources) == 2
    assert result.confidence >= 0.9

def test_conflicting_evidence_sources():
    """Test CONFLICTING state when sources report different values"""
    src1 = SourceModel(
        source_name="Government Order GO-42",
        source_type=SourceType.GOVERNMENT_ORDER,
        authority_level=AuthorityLevel.PRIMARY
    )
    src2 = SourceModel(
        source_name="Press Release",
        source_type=SourceType.NEWS_MEDIA,
        authority_level=AuthorityLevel.SECONDARY
    )
    c1 = CandidateValue(value=679.50, source=src1)
    c2 = CandidateValue(value=750.00, source=src2)

    result = VerificationService.verify_field("estimated_cost", [c1, c2])
    assert result.value is None  # Value set to None during conflict
    assert result.verification_status == VerificationStatus.CONFLICTING
    assert len(result.candidate_values) == 2
    assert len(result.sources) == 2

def test_gemini_extractor_mock_behavior():
    extractor = GeminiExtractorService(api_key=None)
    src = SourceModel(source_name="Test Source", source_type=SourceType.OTHER)
    # Empty content should return empty dict safely
    res = extractor.extract_from_evidence("Uppal Corridor", src, "")
    assert res == {}

def test_research_api_endpoint_structure():
    response = client.post(
        "/api/v1/research/project",
        json={"project_name": "Uppal Elevated Corridor"},
        headers=API_KEY_HEADER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_name_query"] == "Uppal Elevated Corridor"
    assert "project" in data
    assert "sources" in data
    assert "field_verifications" in data
    assert "research_metadata" in data
    assert data["research_metadata"]["research_status"] in ("COMPLETED", "NOT_IMPLEMENTED")
    # Ensure all required fields exist in schema with default NOT_FOUND
    assert data["project"]["tender_id"]["verification_status"] == "NOT_FOUND"
    assert data["project"]["tender_id"]["value"] is None
