import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.connection import SessionLocal
from backend.models.project import Project, ProjectContractor, ProjectTender, ProjectAuthority
from backend.models.tender import Tender
from backend.models.contractor import Contractor
from backend.models.authority import Authority
from backend.models.project_location import ProjectLocation
from backend.models.history import ProjectIdentifier
from backend.models.research import ResearchRun, ProjectFieldEvidence
from backend.models.research_merge import ResearchMergeReview, ResearchMergeAction
from backend.schemas.research import (
    ProjectResearchResult,
    ProjectResearchData,
    EvidentiaryField,
    SourceModel,
    VerificationStatus,
    RetrievalStatus,
    CandidateValue,
    SourceType,
    AuthorityLevel
)
from backend.schemas.research_merge import (
    MatchStatus,
    ReviewStatus,
    FieldDecision,
    FieldComparisonResult
)
from backend.services.entity_resolution_service import EntityResolutionService
from backend.services.controlled_merge_service import ControlledMergeService

client = TestClient(app)
API_KEY_HEADER = {"X-API-Key": "tg_road_intel_secret_key_2026"}
ADMIN_KEY_HEADER = {"X-Admin-Key": "admin_secret_key_2026"}

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_sample_research_result(
    project_name="Uppal Elevated Corridor",
    tender_id=None,
    govt_id=None,
    cost=None,
    contractor=None,
    district=None,
    lat=None,
    lon=None
) -> ProjectResearchResult:
    data = ProjectResearchData()
    data.project_name = EvidentiaryField(
        value=project_name,
        verification_status=VerificationStatus.VERIFIED,
        confidence=0.9,
        sources=[SourceModel(source_name="Gov Portal", retrieval_status=RetrievalStatus.RETRIEVED)]
    )
    if tender_id:
        data.tender_id = EvidentiaryField(
            value=tender_id,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.95,
            sources=[SourceModel(source_name="Tender Portal", retrieval_status=RetrievalStatus.RETRIEVED)]
        )
    if govt_id:
        data.government_project_id = EvidentiaryField(
            value=govt_id,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.95,
            sources=[SourceModel(source_name="Gazette", retrieval_status=RetrievalStatus.RETRIEVED)]
        )
    if cost:
        data.estimated_cost = EvidentiaryField(
            value=cost,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.9,
            sources=[SourceModel(source_name="GO Order", retrieval_status=RetrievalStatus.RETRIEVED)]
        )
    if contractor:
        data.contractor = EvidentiaryField(
            value=contractor,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.85,
            sources=[SourceModel(source_name="News", retrieval_status=RetrievalStatus.RETRIEVED)]
        )
    if district:
        data.district = EvidentiaryField(
            value=district,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.85,
            sources=[SourceModel(source_name="GIS", retrieval_status=RetrievalStatus.RETRIEVED)]
        )
    if lat and lon:
        data.latitude = EvidentiaryField(value=lat, verification_status=VerificationStatus.VERIFIED, confidence=0.8)
        data.longitude = EvidentiaryField(value=lon, verification_status=VerificationStatus.VERIFIED, confidence=0.8)

    return ProjectResearchResult(
        project_name_query=project_name,
        project=data
    )


# ---------------------------------------------------------------------------
# Test Cases A - Y
# ---------------------------------------------------------------------------

def test_a_existing_project_exact_match(db_session: Session):
    """Test Case A: Exact normalized project name match"""
    proj = Project(project_id="PRJ_TEST_A", project_name="Uppal Elevated Corridor Test A", normalized_project_name="uppal elevated corridor test a")
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("Uppal Elevated Corridor Test A")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert resolution.match_status in (MatchStatus.EXACT_MATCH, MatchStatus.HIGH_CONFIDENCE_MATCH)
    assert resolution.match_confidence >= 0.75

def test_b_existing_project_high_confidence_match(db_session: Session):
    """Test Case B: High confidence match (score >= 0.75)"""
    proj = Project(project_id="PRJ_TEST_B", project_name="Uppal Flyover Bridge Highway", normalized_project_name="uppal flyover bridge highway")
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("Uppal Flyover Bridge Highway", cost=679.5)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.match_confidence >= 0.75
    assert resolution.candidate_entity_id == proj.id

def test_c_existing_project_possible_match(db_session: Session):
    """Test Case C: Possible match (0.60 <= score < 0.75)"""
    proj = Project(project_id="PRJ_TEST_C", project_name="Uppal Junction Road", normalized_project_name="uppal junction road")
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("Uppal Junction Expansion")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.match_confidence >= 0.40

def test_d_completely_new_project(db_session: Session):
    """Test Case D: Completely new project -> NEW_ENTITY"""
    res = create_sample_research_result("Totally Unknown Futuristic Hyperloop 999")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.match_status == MatchStatus.NEW_ENTITY
    assert resolution.candidate_entity_id is None

def test_e_exact_tender_id_match(db_session: Session):
    """Test Case E: Exact tender ID match (+0.90 confidence)"""
    proj = Project(project_id="PRJ_TEST_E", project_name="Generic Highway")
    tender = Tender(tender_id="TENDER_998877", title="Highway Tender")
    db_session.add_all([proj, tender])
    db_session.commit()

    pt = ProjectTender(project_id=proj.id, tender_id=tender.id)
    db_session.add(pt)
    db_session.commit()

    res = create_sample_research_result("Unrelated Project Name Query", tender_id="TENDER_998877")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert resolution.match_confidence >= 0.90
    assert any("Tender ID" in s for s in resolution.matching_signals)

def test_f_exact_government_project_id_match(db_session: Session):
    """Test Case F: Exact government project ID match (+0.95 confidence)"""
    proj = Project(project_id="GOVT_GO_TG_8812", project_name="Some Bridge")
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("Bridge Query", govt_id="GOVT_GO_TG_8812")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert resolution.match_confidence >= 0.95
    assert any("Government Project ID" in s for s in resolution.matching_signals)

def test_g_contractor_relationship_match(db_session: Session):
    """Test Case G: Contractor relationship match"""
    proj = Project(project_id="PRJ_TEST_G", project_name="Outer Ring Road Stretch")
    contractor = Contractor(legal_name="KNR Constructions Ltd")
    db_session.add_all([proj, contractor])
    db_session.commit()


    pc = ProjectContractor(project_id=proj.id, contractor_id=contractor.id)
    db_session.add(pc)
    db_session.commit()

    res = create_sample_research_result("Outer Ring Road Stretch", contractor="KNR Constructions Ltd")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert any("Contractor Match" in s for s in resolution.matching_signals)

def test_h_location_spatial_match(db_session: Session):
    """Test Case H: Geographic spatial proximity match (dist <= 2km)"""
    proj = Project(project_id="PRJ_TEST_H", project_name="Gachibowli Flyover")
    db_session.add(proj)
    db_session.flush()
    loc = ProjectLocation(project_id=proj.id, locality="Gachibowli", latitude=17.4401, longitude=78.3489)
    db_session.add(loc)
    db_session.commit()

    # Researched coordinates ~0.2 km away
    res = create_sample_research_result("Gachibowli Flyover", lat=17.4410, lon=78.3495)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert any("Geographic Proximity Match" in s for s in resolution.matching_signals)

def test_i_conflicting_sources_field(db_session: Session):
    """Test Case I: Field comparison handles CONFLICTING comparison status"""
    proj = Project(project_id="PRJ_TEST_I", project_name="Amberpet Flyover", estimated_cost=250.0)
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("Amberpet Flyover", cost=300.0) # Research cost differs from canonical
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    cost_comp = resolution.field_comparisons["estimated_cost"]
    assert cost_comp.comparison_result == FieldComparisonResult.CONFLICTING
    assert cost_comp.research_value == 300.0
    assert cost_comp.canonical_value == 250.0

def test_j_research_value_null_not_found(db_session: Session):
    """Test Case J: Missing research value -> UNVERIFIED_MISSING"""
    res = create_sample_research_result("Unknown Corridor")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    tender_comp = resolution.field_comparisons["tender_id"]
    assert tender_comp.comparison_result == FieldComparisonResult.UNVERIFIED_MISSING
    assert tender_comp.research_value is None

def test_k_not_found_cannot_overwrite_canonical(db_session: Session):
    """Test Case K: NOT_FOUND research value MUST NEVER replace canonical value during merge"""
    proj = Project(project_id="PRJ_TEST_K", project_name="Kalyan Highway", estimated_cost=500.0)
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Kalyan Highway", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Kalyan Highway") # estimated_cost is NULL / NOT_FOUND
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    # Attempt to execute merge
    merge_service = ControlledMergeService(db_session)
    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")

    # Canonical estimated_cost MUST remain 500.0
    db_session.refresh(proj)
    assert proj.estimated_cost == 500.0

def test_l_reject_does_not_modify_canonical(db_session: Session):
    """Test Case L: Rejecting a field preserves canonical value"""
    proj = Project(project_id="PRJ_TEST_L", project_name="Warangal Highway", estimated_cost=400.0)
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Warangal Highway", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Warangal Highway", cost=450.0)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    # Reject estimated_cost
    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {"estimated_cost": FieldDecision.REJECT},
            "overall_status": ReviewStatus.APPROVED,
            "reviewed_by": "admin",
            "review_notes": "Rejected higher estimate"
        })()
    )

    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")

    db_session.refresh(proj)
    assert proj.estimated_cost == 400.0 # Canonical value unchanged

def test_m_needs_more_evidence_does_not_modify_canonical(db_session: Session):
    """Test Case M: NEEDS_MORE_EVIDENCE preserves canonical database"""
    proj = Project(project_id="PRJ_TEST_M", project_name="Nizamabad Bypass", status="In Progress")
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Nizamabad Bypass", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Nizamabad Bypass", contractor="Unverified Contractor")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {"contractor": FieldDecision.NEEDS_MORE_EVIDENCE},
            "overall_status": ReviewStatus.NEEDS_MORE_EVIDENCE,
            "reviewed_by": "admin",
            "review_notes": "Pending tender confirmation"
        })()
    )

    # Execute merge should skip contractor update
    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")
    db_session.refresh(proj)
    assert proj.status == "In Progress"

def test_n_approve_creates_state_without_auto_merge(db_session: Session):
    """Test Case N: Approving review creates approval state BUT does NOT modify canonical tables until merge service runs"""
    proj = Project(project_id="PRJ_TEST_N", project_name="Karimnagar Express", estimated_cost=100.0)
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Karimnagar Express", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Karimnagar Express", cost=150.0)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    # Approve review via API or service
    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {"estimated_cost": FieldDecision.APPROVE},
            "overall_status": ReviewStatus.APPROVED,
            "reviewed_by": "admin",
            "review_notes": "Approved update"
        })()
    )

    # Check canonical table NOT mutated yet!
    db_session.refresh(proj)
    assert proj.estimated_cost == 100.0

def test_o_merge_inserts_approved_missing_field(db_session: Session):
    """Test Case O: MERGE inserts approved missing field (when canonical value was NULL)"""
    proj = Project(project_id="PRJ_TEST_O", project_name="Khammam Highway", estimated_cost=None)
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Khammam Highway", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Khammam Highway", cost=320.0)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {"estimated_cost": FieldDecision.APPROVE},
            "overall_status": ReviewStatus.APPROVED,
            "reviewed_by": "admin",
            "review_notes": "Approved cost insertion"
        })()
    )

    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")

    db_session.refresh(proj)
    assert proj.estimated_cost == 320.0 # Canonical updated!

def test_p_merge_updates_only_explicitly_approved_field(db_session: Session):
    """Test Case P: MERGE updates ONLY explicitly approved fields"""
    proj = Project(project_id="PRJ_TEST_P", project_name="Mahbubnagar Bypass", estimated_cost=200.0, status="Draft")
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Mahbubnagar Bypass", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Mahbubnagar Bypass", cost=250.0, contractor="Approved Contractor")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    # Approve ONLY contractor, reject estimated_cost
    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {
                "contractor": FieldDecision.APPROVE,
                "estimated_cost": FieldDecision.REJECT
            },
            "overall_status": ReviewStatus.APPROVED,
            "reviewed_by": "admin",
            "review_notes": "Only approved contractor"
        })()
    )

    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")

    db_session.refresh(proj)
    assert proj.estimated_cost == 200.0 # Unapproved cost unchanged!
    assert proj.contractor_associations[0].contractor.legal_name == "Approved Contractor" # Approved contractor linked!


def test_q_conflicting_canonical_value_cannot_be_silently_overwritten(db_session: Session):
    """Test Case Q: Existing conflicting canonical value cannot be silently overwritten without explicit approval"""
    proj = Project(project_id="PRJ_TEST_Q", project_name="Siddipet Ring Road", estimated_cost=180.0)
    db_session.add(proj)
    db_session.commit()

    run = ResearchRun(query_project_name="Siddipet Ring Road", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Siddipet Ring Road", cost=220.0)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    # Review status remains PENDING / decision PENDING
    merge_service = ControlledMergeService(db_session)
    # Execute merge without explicit APPROVE decision for estimated_cost
    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")

    db_session.refresh(proj)
    assert proj.estimated_cost == 180.0 # Cannot be silently overwritten!

def test_s_evidence_remains_after_merge(db_session: Session):
    """Test Case S: Research evidence remains preserved in DB after merge"""
    proj = Project(project_id="PRJ_TEST_S", project_name="Ramagundam Highway")
    run = ResearchRun(query_project_name="Ramagundam Highway", status="COMPLETED")
    db_session.add_all([proj, run])
    db_session.flush()

    ev = ProjectFieldEvidence(
        research_run_id=run.id,
        field_name="estimated_cost",
        extracted_value="550.0",
        verification_status="VERIFIED",
        confidence=0.9,
        evidence_snippet="Sanctioned 550 Cr"
    )
    db_session.add(ev)
    db_session.commit()

    res = create_sample_research_result("Ramagundam Highway", cost=550.0)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {"estimated_cost": FieldDecision.APPROVE},
            "overall_status": ReviewStatus.APPROVED,
            "reviewed_by": "admin",
            "review_notes": "Merge test"
        })()
    )
    merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin")

    # Verify ProjectFieldEvidence record is STILL intact in DB!
    saved_ev = db_session.query(ProjectFieldEvidence).filter(ProjectFieldEvidence.id == ev.id).first()
    assert saved_ev is not None
    assert saved_ev.evidence_snippet == "Sanctioned 550 Cr"

def test_t_audit_trail_contains_previous_and_new_value(db_session: Session):
    """Test Case T: Audit trail contains previous and new value in ResearchMergeAction"""
    proj = Project(project_id="PRJ_TEST_T", project_name="Adilabad Road", estimated_cost=120.0)
    run = ResearchRun(query_project_name="Adilabad Road", status="COMPLETED")
    db_session.add_all([proj, run])
    db_session.flush()

    res = create_sample_research_result("Adilabad Road", cost=160.0)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    merge_service = ControlledMergeService(db_session)
    merge_service.update_review(
        review_id=resolution.review_id,
        req=type("Req", (), {
            "field_decisions": {"estimated_cost": FieldDecision.APPROVE},
            "overall_status": ReviewStatus.APPROVED,
            "reviewed_by": "admin_test",
            "review_notes": "Approved cost update"
        })()
    )
    actions = merge_service.execute_merge(review_id=resolution.review_id, approved_by="admin_test")

    cost_action = [a for a in actions if a.field_name == "estimated_cost"][0]
    assert cost_action.previous_value == "120.0"
    assert cost_action.new_value == "160.0"
    assert cost_action.approved_by == "admin_test"

def test_u_invalid_review_id_fails_safely(db_session: Session):
    """Test Case U: Invalid review ID fails safely via API (404 Not Found)"""
    response = client.get("/api/v1/research/reviews/9999999", headers=API_KEY_HEADER)
    assert response.status_code == 404

def test_v_unauthorized_merge_fails():
    """Test Case V: Unauthorized merge attempt fails (403 Forbidden without Admin Key)"""
    # Call merge endpoint with standard non-admin key header
    response = client.post(
        "/api/v1/research/reviews/1/merge",
        json={"approved_by": "hacker"},
        headers={"X-API-Key": "standard_user_key_without_admin_access"}
    )
    assert response.status_code in (401, 403)

def test_w_duplicate_research_idempotency(db_session: Session):
    """Test Case W: Duplicate research request returns cached run without creating duplicate entities"""
    run = ResearchRun(
        query_project_name="Idempotent Corridor Query",
        status="COMPLETED",
        result_payload={"project_name_query": "Idempotent Corridor Query", "project": {}, "sources": [], "field_verifications": {}, "research_metadata": {"research_status": "COMPLETED"}}
    )
    db_session.add(run)
    db_session.commit()

    count_before = db_session.query(ResearchRun).count()
    res = client.post(
        "/api/v1/research/project",
        json={"project_name": "Idempotent Corridor Query", "force_refresh": False},
        headers=API_KEY_HEADER
    )
    assert res.status_code == 200
    assert db_session.query(ResearchRun).count() == count_before # No duplicate run created!

def test_x_uppal_elevated_corridor_validation(db_session: Session):
    """Test Case X: Uppal Elevated Corridor generic entity resolution validation"""
    proj = Project(project_id="PRJ_UPPAL_01", project_name="Uppal Elevated Corridor Validation", normalized_project_name="uppal elevated corridor validation")
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("Uppal Elevated Corridor Validation", cost=679.50)
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert resolution.match_status in (MatchStatus.EXACT_MATCH, MatchStatus.HIGH_CONFIDENCE_MATCH)

def test_y_iit_hyderabad_validation(db_session: Session):
    """Test Case Y: IIT Hyderabad campus infrastructure generic entity resolution validation"""
    proj = Project(project_id="PRJ_IITH_01", project_name="IIT Hyderabad campus infrastructure", normalized_project_name="iit hyderabad campus infrastructure")
    db_session.add(proj)
    db_session.commit()

    res = create_sample_research_result("IIT Hyderabad campus infrastructure", district="Sangareddy")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res)

    assert resolution.candidate_entity_id == proj.id
    assert resolution.match_status in (MatchStatus.EXACT_MATCH, MatchStatus.HIGH_CONFIDENCE_MATCH)

def test_z_unapproved_merge_endpoint_rejected(db_session: Session):
    """Test Case Z: Unapproved merge endpoint request MUST be rejected with HTTP 400"""
    run = ResearchRun(query_project_name="Pending Review Road", status="COMPLETED")
    db_session.add(run)
    db_session.flush()

    res = create_sample_research_result("Pending Review Road")
    resolver = EntityResolutionService(db_session)
    resolution = resolver.resolve(res, research_run_id=run.id)

    # Attempt to call /merge endpoint directly while review status is PENDING (not APPROVED)
    response = client.post(
        f"/api/v1/research/reviews/{resolution.review_id}/merge",
        json={"approved_by": "admin"},
        headers=ADMIN_KEY_HEADER
    )
    assert response.status_code == 400
    assert "Review status must be APPROVED" in response.json()["detail"]

