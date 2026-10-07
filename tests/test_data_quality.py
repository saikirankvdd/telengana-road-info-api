import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from backend.main import app
from backend.database.connection import SessionLocal
from backend.models.project import Project, ProjectTender
from backend.models.tender import Tender
from backend.models.research import ResearchRun
from backend.models.data_quality import ResearchQualityReportModel, ResearchQualityIssueModel
from backend.schemas.research import (
    ProjectResearchResult,
    ProjectResearchData,
    EvidentiaryField,
    SourceModel,
    VerificationStatus,
    RetrievalStatus,
    CandidateValue,
    SourceType,
    AuthorityLevel,
    ResearchMetadata,
    ResearchStatus
)
from backend.schemas.data_quality import QualityClass, QualitySeverity, QualityStatus
from backend.services.data_quality.data_quality_service import DataQualityService
from backend.services.data_quality.field_validator import FieldValidator
from backend.services.data_quality.cross_field_validator import CrossFieldValidator
from backend.services.data_quality.source_quality_service import SourceQualityService

client = TestClient(app)
API_KEY_HEADER = {"X-API-Key": "tg_road_intel_secret_key_2026"}


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_sample_research_payload(
    project_name="Uppal Elevated Corridor",
    tender_id=None,
    cost=None,
    awarded_cost=None,
    contractor=None,
    district="Medchal-Malkajgiri",
    lat=17.3984,
    lon=78.5583,
    road_len=6.2,
    pub_date=None,
    sub_deadline=None,
    start_date=None,
    end_date=None,
    status="In Progress",
    with_source_url=True
) -> ProjectResearchResult:
    data = ProjectResearchData()

    sources = []
    if with_source_url:
        sources = [SourceModel(
            source_id="src_01",
            source_name="Telangana Open Data Portal",
            source_url="https://data.telangana.gov.in/dataset/TOD_001",
            source_type=SourceType.GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            retrieval_status=RetrievalStatus.RETRIEVED,
            evidence_text="Sanctioned project details"
        )]

    data.project_name = EvidentiaryField(
        value=project_name,
        verification_status=VerificationStatus.VERIFIED,
        confidence=0.9,
        sources=sources,
        retrieved_at=datetime.now(timezone.utc).isoformat()
    )

    if tender_id:
        data.tender_id = EvidentiaryField(
            value=tender_id,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.95,
            sources=sources,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
    if cost is not None:
        data.estimated_cost = EvidentiaryField(
            value=cost,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.9,
            sources=sources,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
    if awarded_cost is not None:
        data.awarded_cost = EvidentiaryField(
            value=awarded_cost,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.9,
            sources=sources,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
    if contractor:
        data.contractor = EvidentiaryField(
            value=contractor,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.85,
            sources=sources,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
    if district:
        data.district = EvidentiaryField(
            value=district,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.9,
            sources=sources,
            retrieved_at=datetime.now(timezone.utc).isoformat()
        )
    if lat is not None and lon is not None:
        data.latitude = EvidentiaryField(value=lat, verification_status=VerificationStatus.VERIFIED, confidence=0.85, sources=sources)
        data.longitude = EvidentiaryField(value=lon, verification_status=VerificationStatus.VERIFIED, confidence=0.85, sources=sources)
    if road_len is not None:
        data.road_length_km = EvidentiaryField(value=road_len, verification_status=VerificationStatus.VERIFIED, confidence=0.85, sources=sources)
    if pub_date:
        data.publication_date = EvidentiaryField(value=pub_date, verification_status=VerificationStatus.VERIFIED, sources=sources)
    if sub_deadline:
        data.submission_deadline = EvidentiaryField(value=sub_deadline, verification_status=VerificationStatus.VERIFIED, sources=sources)
    if start_date:
        data.contract_start_date = EvidentiaryField(value=start_date, verification_status=VerificationStatus.VERIFIED, sources=sources)
    if end_date:
        data.contract_end_date = EvidentiaryField(value=end_date, verification_status=VerificationStatus.VERIFIED, sources=sources)
    if status:
        data.status = EvidentiaryField(value=status, verification_status=VerificationStatus.VERIFIED, sources=sources)

    return ProjectResearchResult(
        project_name_query=project_name,
        project=data,
        sources=sources,
        field_verifications={},
        research_metadata=ResearchMetadata(
            research_status=ResearchStatus.COMPLETED,
            sources_selected=len(sources),
            sources_accessed=len(sources)
        )
    )


# 1. Valid project passes validation
def test_01_valid_project_passes_validation(db_session: Session):
    payload = create_sample_research_payload("Uppal Elevated Corridor", cost=679.50, contractor="NCC Ltd")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.quality_class in (QualityClass.EXCELLENT, QualityClass.GOOD)
    assert report.merge_eligible is True
    assert report.fields_invalid == 0


# 2. Missing fields detection
def test_02_missing_fields_detection(db_session: Session):
    payload = create_sample_research_payload("Minimal Road")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.fields_missing > 5


# 3. Empty string validation
def test_03_empty_string_validation():
    status, issues, norm = FieldValidator.validate_string("contractor", "   ")
    assert status == QualityStatus.INVALID
    assert len(issues) == 1
    assert issues[0].rule_name == "EMPTY_STRING"


# 4. Placeholder values detection
def test_04_placeholder_values_detection():
    for ph in ("N/A", "unknown", "null", "none", "not available"):
        status, issues, norm = FieldValidator.validate_string("authority", ph)
        assert status == QualityStatus.INVALID
        assert issues[0].rule_name == "PLACEHOLDER_STRING"


# 5. Negative cost validation
def test_05_negative_cost_validation():
    status, issues = FieldValidator.validate_financial("estimated_cost", -500.0)
    assert status == QualityStatus.INVALID
    assert issues[0].rule_name == "NEGATIVE_COST"


# 6. Suspicious cost validation
def test_06_suspicious_cost_validation():
    status, issues = FieldValidator.validate_financial("estimated_cost", 99999.0)
    assert status == QualityStatus.SUSPICIOUS
    assert issues[0].rule_name == "UNREALISTIC_HIGH_COST"


# 7. Awarded cost > estimated cost validation
def test_07_awarded_cost_greater_than_estimated():
    status, issues = FieldValidator.validate_financial("awarded_cost", 1500.0, estimated_cost=500.0)
    assert status == QualityStatus.SUSPICIOUS
    assert issues[0].rule_name == "AWARDED_EXCEEDS_ESTIMATED"


# 8. Invalid latitude range
def test_08_invalid_latitude():
    statuses, issues = FieldValidator.validate_geographic(lat=105.0, lon=78.5)
    assert statuses["latitude"] == QualityStatus.INVALID
    assert issues[0].rule_name == "INVALID_LATITUDE_RANGE"


# 9. Invalid longitude range
def test_09_invalid_longitude():
    statuses, issues = FieldValidator.validate_geographic(lat=17.5, lon=-200.0)
    assert statuses["longitude"] == QualityStatus.INVALID
    assert issues[0].rule_name == "INVALID_LONGITUDE_RANGE"


# 10. Negative road length
def test_10_negative_road_length():
    statuses, issues = FieldValidator.validate_geographic(lat=17.5, lon=78.5, road_length_km=-10.0)
    assert statuses["road_length_km"] == QualityStatus.INVALID
    assert issues[0].rule_name == "NEGATIVE_ROAD_LENGTH"


# 11. Deadline before publication date
def test_11_deadline_before_publication():
    issues = FieldValidator.validate_date_sequence(
        pub_date_val="2026-05-10",
        sub_deadline_val="2026-04-10"
    )
    assert len(issues) == 1
    assert issues[0].rule_name == "DEADLINE_BEFORE_PUBLICATION"


# 12. Award before publication date
def test_12_award_before_publication():
    issues = FieldValidator.validate_date_sequence(
        pub_date_val="2026-05-10",
        sub_deadline_val="2026-06-10",
        award_date_val="2026-04-01"
    )
    assert len(issues) == 1
    assert issues[0].rule_name == "AWARD_BEFORE_PUBLICATION"


# 13. Contract end before contract start date
def test_13_contract_end_before_start():
    issues = FieldValidator.validate_date_sequence(
        pub_date_val="2026-01-01",
        sub_deadline_val="2026-02-01",
        start_date_val="2026-06-01",
        end_date_val="2025-12-31"
    )
    assert len(issues) == 1
    assert issues[0].rule_name == "END_BEFORE_START_DATE"


# 14. Valid date sequence passes clean
def test_14_valid_date_sequence():
    issues = FieldValidator.validate_date_sequence(
        pub_date_val="2026-01-01",
        sub_deadline_val="2026-02-01",
        award_date_val="2026-03-01",
        start_date_val="2026-04-01",
        end_date_val="2027-04-01"
    )
    assert len(issues) == 0


# 15. Conflicting source values detection
def test_15_conflicting_source_values():
    src1 = SourceModel(source_name="Gov GO", source_url="https://telangana.gov.in/go1")
    src2 = SourceModel(source_name="Media", source_url="https://news.com/art1")
    field = EvidentiaryField(
        value=None,
        verification_status=VerificationStatus.CONFLICTING,
        candidate_values=[
            CandidateValue(value=500.0, source=src1),
            CandidateValue(value=550.0, source=src2)
        ]
    )
    has_conf, issues = SourceQualityService.detect_cross_source_conflicts("estimated_cost", field)
    assert has_conf is True
    assert issues[0].rule_name == "CROSS_SOURCE_CONFLICT"


# 16. Matching primary sources increases quality
def test_16_matching_primary_sources(db_session: Session):
    payload = create_sample_research_payload("Warangal Highway", cost=450.0)
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.cross_source_conflicts == 0


# 17. Unsupported field value (value present but no source)
def test_17_unsupported_field_value():
    field = EvidentiaryField(value="ABC Infra Ltd", verification_status=VerificationStatus.VERIFIED, sources=[])
    status, is_supp, is_stale, issues = SourceQualityService.evaluate_field_provenance("contractor", field)
    assert status == QualityStatus.UNSUPPORTED
    assert is_supp is False


# 18. Missing evidence URL detection
def test_18_missing_evidence_url():
    field = EvidentiaryField(
        value="ABC Infra Ltd",
        verification_status=VerificationStatus.VERIFIED,
        sources=[SourceModel(source_name="Unlinked Source", source_url=None)]
    )
    status, is_supp, is_stale, issues = SourceQualityService.evaluate_field_provenance("contractor", field)
    assert status == QualityStatus.UNSUPPORTED
    assert issues[0].rule_name == "MISSING_SOURCE_URL"


# 19. Stale tender status detection (> 30 days)
def test_19_stale_tender_status():
    old_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    field = EvidentiaryField(
        value="Active",
        verification_status=VerificationStatus.VERIFIED,
        retrieved_at=old_date,
        sources=[SourceModel(source_name="Portal", source_url="https://gov.in")]
    )
    status, is_supp, is_stale, issues = SourceQualityService.evaluate_field_provenance("tender_status", field)
    assert is_stale is True
    assert issues[0].rule_name == "STALE_EVIDENCE"


# 20. Fresh project information (< 30 days)
def test_20_fresh_project_information():
    fresh_date = datetime.now(timezone.utc).isoformat()
    field = EvidentiaryField(
        value="Uppal Corridor",
        verification_status=VerificationStatus.VERIFIED,
        retrieved_at=fresh_date,
        sources=[SourceModel(source_name="Portal", source_url="https://gov.in")]
    )
    status, is_supp, is_stale, issues = SourceQualityService.evaluate_field_provenance("project_name", field)
    assert is_stale is False


# 21. Duplicate project detection
def test_21_duplicate_project_detection(db_session: Session):
    proj = Project(project_id="PRJ_DUP_01", project_name="Karimnagar Bypass Road", normalized_project_name="karimnagar bypass road")
    db_session.add(proj)
    db_session.commit()

    payload = create_sample_research_payload("Karimnagar Bypass Road")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.duplicate_candidates_count >= 1


# 22. Duplicate tender detection
def test_22_duplicate_tender_detection(db_session: Session):
    proj = Project(project_id="PRJ_DUP_02", project_name="Nizamabad Flyover", normalized_project_name="nizamabad flyover")
    t = Tender(tender_id="TND_NZB_999", title="Nizamabad Flyover Tender")
    db_session.add_all([proj, t])
    db_session.commit()
    pt = ProjectTender(project_id=proj.id, tender_id=t.id)
    db_session.add(pt)
    db_session.commit()

    payload = create_sample_research_payload("Nizamabad Flyover", tender_id="TND_NZB_999")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.duplicate_candidates_count >= 1


# 23. Conflicting tender IDs blocks merge
def test_23_conflicting_tender_ids(db_session: Session):
    payload = create_sample_research_payload("Conflict Tender Road")
    payload.project.tender_id = EvidentiaryField(
        value=None,
        verification_status=VerificationStatus.CONFLICTING,
        sources=[SourceModel(source_name="S1", source_url="https://s1.gov")]
    )
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.merge_eligible is False
    assert "CONFLICTING_TENDER_ID" in report.merge_blockers


# 24. Quality score calculation (0.0 to 1.0)
def test_24_quality_score_calculation(db_session: Session):
    payload = create_sample_research_payload("Score Test Road", cost=100.0)
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert 0.0 <= report.overall_quality_score <= 1.0


# 25. Quality class calculation
def test_25_quality_class_calculation(db_session: Session):
    payload = create_sample_research_payload("Class Test Road", cost=100.0, contractor="NCC")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.quality_class in (QualityClass.EXCELLENT, QualityClass.GOOD, QualityClass.FAIR)


# 26. Critical error blocks merge eligibility
def test_26_critical_error_blocks_merge(db_session: Session):
    payload = create_sample_research_payload("Error Road", cost=-500.0) # Invalid negative cost
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.merge_eligible is False
    assert report.fields_invalid >= 1


# 27. Warning does not automatically block merge
def test_27_warning_does_not_block_merge(db_session: Session):
    payload = create_sample_research_payload("Warning Road", cost=60000.0) # High cost warning
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.fields_suspicious >= 1
    assert report.is_quarantined is False


# 28. Quarantine behavior on severe invalid data
def test_28_quarantine_behavior(db_session: Session):
    payload = create_sample_research_payload("Quarantine Road", lat=120.0) # Impossible latitude
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.is_quarantined is True
    assert report.quality_class == QualityClass.QUARANTINED
    assert report.merge_eligible is False


# 29. Validation does not mutate canonical DB (mutation count = 0)
def test_29_validation_does_not_mutate_canonical_db(db_session: Session):
    p_count_before = db_session.query(Project).count()
    t_count_before = db_session.query(Tender).count()

    payload = create_sample_research_payload("Validation Safety Road", cost=250.0)
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)

    assert db_session.query(Project).count() == p_count_before
    assert db_session.query(Tender).count() == t_count_before


# 30. Revalidation endpoint works
def test_30_revalidation_endpoint(db_session: Session):
    run = ResearchRun(
        query_project_name="Revalidate Corridor",
        status="COMPLETED",
        result_payload=create_sample_research_payload("Revalidate Corridor", cost=300.0).model_dump()
    )
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/api/v1/research/quality/{run.id}/revalidate", headers=API_KEY_HEADER)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["project_name"] == "Revalidate Corridor"
    assert res_data["overall_quality_score"] > 0.5


# 31. Uppal Elevated Corridor quality validation
def test_31_uppal_elevated_corridor_quality_validation(db_session: Session):
    payload = create_sample_research_payload("Uppal Elevated Corridor", cost=679.50, road_len=6.2, lat=17.3984, lon=78.5583)
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.quality_class in (QualityClass.EXCELLENT, QualityClass.GOOD)
    assert report.merge_eligible is True


# 32. IIT Hyderabad quality validation
def test_32_iit_hyderabad_quality_validation(db_session: Session):
    payload = create_sample_research_payload("IIT Hyderabad campus civil infrastructure", district="Sangareddy", lat=17.5947, lon=78.1230)
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.quality_class in (QualityClass.EXCELLENT, QualityClass.GOOD)
    assert report.merge_eligible is True


# 33. Nonexistent project remains NOT_FOUND
def test_33_nonexistent_project_validation(db_session: Session):
    payload = create_sample_research_payload("Nonexistent Arbitrary Test Highway")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.duplicate_candidates_count == 0


# 34. Task 4 review integration check
def test_34_task_4_review_integration(db_session: Session):
    run = ResearchRun(
        query_project_name="Integration Test Road",
        status="COMPLETED",
        result_payload=create_sample_research_payload("Integration Test Road", cost=150.0).model_dump()
    )
    db_session.add(run)
    db_session.commit()

    service = DataQualityService(db_session)
    report = service.validate_research_result(create_sample_research_payload("Integration Test Road", cost=150.0), research_run_id=run.id)

    saved_report = db_session.query(ResearchQualityReportModel).filter(
        ResearchQualityReportModel.research_run_id == run.id
    ).first()
    assert saved_report is not None
    assert saved_report.research_run_id == run.id


# 35. Task 3 research pipeline validation integration
def test_35_task_3_research_integration_api(db_session: Session):
    res = client.post(
        "/api/v1/research/validate",
        json={"project_name": "Task 3 Integration Road", "force_refresh": True},
        headers=API_KEY_HEADER
    )
    assert res.status_code == 200
    res_json = res.json()
    assert "overall_quality_score" in res_json
    assert "quality_class" in res_json


# 36. Task 5 source metadata integration check
def test_36_task_5_source_metadata_integration(db_session: Session):
    payload = create_sample_research_payload("Task 5 Metadata Road")
    service = DataQualityService(db_session)
    report = service.validate_research_result(payload)
    assert report.fields_checked > 10
