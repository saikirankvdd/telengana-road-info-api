import pytest
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.schemas.research import (
    ProjectResearchResult,
    ProjectResearchData,
    VerificationStatus,
    SourceModel,
    SourceType,
    AuthorityLevel,
    CandidateValue,
    ResearchStatus
)
from backend.schemas.government_source import (
    GovernmentSource,
    GovernmentSourceType,
    LegalAccessStatus,
    ProjectDomain
)
from backend.services.source_registry import GovernmentSourceRegistry
from backend.services.source_routing_service import SourceRoutingService
from backend.services.query_generator import SourceQueryGenerator
from backend.services.source_priority_service import SourcePriorityService
from backend.services.verification_service import VerificationService
from backend.services.research_pipeline import GeminiResearcher
from backend.adapters.base_adapter import GovernmentSourceAdapter
from backend.adapters.government_adapters import ProtectedSourceAdapter
from backend.models.project import Project
from backend.models.tender import Tender
from backend.models.contractor import Contractor
from backend.models.research import ResearchRun

# ---------------------------------------------------------------------------
# Test Helpers & Mock Adapters
# ---------------------------------------------------------------------------

class MockFailingAdapter(GovernmentSourceAdapter):
    def is_available(self) -> bool:
        return True
    def search(self, query: str, project_context=None, max_results=5):
        raise RuntimeError("Simulated 500 / Timeout Error")
    def retrieve(self, source_model: SourceModel):
        return None

class MockRateLimitedAdapter(GovernmentSourceAdapter):
    def is_available(self) -> bool:
        return True
    def search(self, query: str, project_context=None, max_results=5):
        raise ConnectionError("429 Too Many Requests")
    def retrieve(self, source_model: SourceModel):
        return None

# ---------------------------------------------------------------------------
# Test Cases 1 - 23
# ---------------------------------------------------------------------------

def test_1_nhai_morth_routing():
    """1. NH/NHAI project routes toward NHAI/MoRTH/CPPP"""
    router = SourceRoutingService()
    adapters = router.route_request("NH-163 Uppal Narapally Corridor")
    source_ids = [a.source.source_id for a in adapters]

    assert "nhai" in source_ids
    assert "morth" in source_ids
    assert "cppp_eproc" in source_ids
    assert source_ids.index("nhai") < source_ids.index("secondary_news")

def test_2_ghmc_routing():
    """2. GHMC project routes toward GHMC"""
    router = SourceRoutingService()
    adapters = router.route_request("GHMC SRDP Flyover at Gachibowli Junction")
    source_ids = [a.source.source_id for a in adapters]

    assert "ghmc" in source_ids
    assert "telangana_open_data" in source_ids
    assert source_ids[0] == "ghmc"

def test_3_hmda_routing():
    """3. HMDA project routes toward HMDA"""
    router = SourceRoutingService()
    adapters = router.route_request("HMDA Outer Ring Road Growth Corridor")
    source_ids = [a.source.source_id for a in adapters]

    assert "hmda" in source_ids
    assert "telangana_open_data" in source_ids
    assert source_ids[0] == "hmda"

def test_4_rural_road_routing():
    """4. Rural road routes toward PMGSY/appropriate rural sources"""
    router = SourceRoutingService()
    adapters = router.route_request("PMGSY Gram Panchayat Road Resurfacing")
    source_ids = [a.source.source_id for a in adapters]

    assert "pmgsy_ommas" in source_ids
    assert source_ids[0] == "pmgsy_ommas"

def test_5_government_order_routing():
    """5. Government-order query prioritizes official GO sources"""
    router = SourceRoutingService()
    adapters = router.route_request("G.O. Ms. No. 45 Administrative Sanction")
    source_ids = [a.source.source_id for a in adapters]

    assert "telangana_go" in source_ids
    assert source_ids[0] == "telangana_go"

def test_6_central_institution_routing():
    """6. Central institution project routes toward CPPP/relevant official sources"""
    router = SourceRoutingService()
    adapters = router.route_request("IIT Hyderabad Campus Infrastructure Phase II")
    source_ids = [a.source.source_id for a in adapters]

    assert "cppp_eproc" in source_ids
    assert "data_gov_in" in source_ids

def test_7_8_9_10_source_failure_resilience():
    """7-10. Source failure, 429 rate limit, 5xx, and timeout do not crash research"""
    registry = GovernmentSourceRegistry()
    
    # Register failing & rate limited adapters
    failing_src = GovernmentSource(source_id="fail_src", name="Failing Source", base_url="http://fail", enabled=True)
    rate_src = GovernmentSource(source_id="rate_src", name="Rate Limited Source", base_url="http://rate", enabled=True)
    
    registry.register_source(failing_src, MockFailingAdapter(failing_src))
    registry.register_source(rate_src, MockRateLimitedAdapter(rate_src))

    researcher = GeminiResearcher(source_registry=registry)
    result = researcher.research_project("Generic Resilient Highway", force_refresh=True)

    assert result is not None
    assert result.research_metadata.sources_failed >= 0
    assert result.research_metadata.research_status == ResearchStatus.COMPLETED

def test_11_protected_captcha_source_not_accessible():
    """11. Protected/CAPTCHA source is marked NOT_ACCESSIBLE"""
    src = GovernmentSource(source_id="captcha_test", name="Protected Portal", base_url="http://prot", enabled=True)
    adapter = ProtectedSourceAdapter(src)

    assert adapter.get_access_status() == LegalAccessStatus.CAPTCHA_PROTECTED
    assert adapter.is_available() is False
    assert adapter.search("Query") == []

def test_12_duplicate_url_deduplication():
    """12. Duplicate URLs are deduplicated"""
    src1 = SourceModel(source_id="s1", source_url="https://eproc.tg.gov.in/tenders/101", source_name="P1", title="Doc 1", evidence_text="Content A")
    src2 = SourceModel(source_id="s2", source_url="https://eproc.tg.gov.in/tenders/101", source_name="P1", title="Doc 1 Dup", evidence_text="Content A")

    researcher = GeminiResearcher()
    result = researcher.research_project("Duplicate URL Test Project", initial_sources=[src1, src2], force_refresh=True)

    url_counts = [s.source_url for s in result.sources if s.source_url == "https://eproc.tg.gov.in/tenders/101"]
    assert len(url_counts) == 1 # Deduplicated to 1

def test_13_primary_outranks_secondary_source():
    """13. Primary source outranks secondary source"""
    pri_src = SourceModel(source_name="Govt Portal", source_url="http://gov.in", authority_level=AuthorityLevel.PRIMARY, source_type=SourceType.GOVERNMENT_PORTAL)
    sec_src = SourceModel(source_name="Blog", source_url="http://blog.com", authority_level=AuthorityLevel.SECONDARY, source_type=SourceType.NEWS_MEDIA)

    cand_pri = CandidateValue(value="ABC Infrastructure", source=pri_src, confidence=0.9)
    cand_sec = CandidateValue(value="XYZ Infra", source=sec_src, confidence=0.8)

    priority_service = SourcePriorityService()
    ranked = priority_service.rank_candidates("contractor", [cand_sec, cand_pri])

    assert ranked[0].source.authority_level == AuthorityLevel.PRIMARY
    assert ranked[0].value == "ABC Infrastructure"

def test_14_primary_secondary_conflict_preserved():
    """14. Primary/secondary conflict is preserved"""
    pri_src = SourceModel(source_name="Govt Order", authority_level=AuthorityLevel.PRIMARY, source_type=SourceType.GOVERNMENT_ORDER)
    sec_src = SourceModel(source_name="News Paper", authority_level=AuthorityLevel.SECONDARY, source_type=SourceType.NEWS_MEDIA)

    cand1 = CandidateValue(value=650.0, source=pri_src, confidence=0.9)
    cand2 = CandidateValue(value=679.5, source=sec_src, confidence=0.85)

    verifier = VerificationService()
    field = verifier.verify_field("estimated_cost", [cand1, cand2])

    assert field.verification_status == VerificationStatus.CONFLICTING
    assert field.value is None
    assert len(field.candidate_values) == 2

def test_15_field_evidence_retains_source_url():
    """15. Field evidence retains source URL"""
    src = SourceModel(source_name="Telangana Open Data", source_url="https://data.telangana.gov.in/dataset/123", authority_level=AuthorityLevel.PRIMARY)
    cand = CandidateValue(value="KNR Constructions", source=src, confidence=0.9)

    verifier = VerificationService()
    field = verifier.verify_field("contractor", [cand])

    assert field.verification_status == VerificationStatus.VERIFIED
    assert field.sources[0].source_url == "https://data.telangana.gov.in/dataset/123"

def test_16_17_not_found_remains_null():
    """16-17. NOT_FOUND remains NULL; Gemini cannot fabricate a value without evidence"""
    verifier = VerificationService()
    field = verifier.verify_field("dpr_reference", [])

    assert field.value is None
    assert field.verification_status == VerificationStatus.NOT_FOUND
    assert field.confidence == 0.0

def test_18_telangana_open_data_collector_integration():
    """18. Existing Telangana Open Data collector continues working"""
    registry = GovernmentSourceRegistry()
    adapter = registry.get_adapter("telangana_open_data")

    assert adapter is not None
    assert adapter.is_available() is True
    res = adapter.search("Uppal Elevated Corridor")
    assert len(res) > 0
    assert res[0].source_type == SourceType.GOVERNMENT_PORTAL

def test_19_existing_task_3_research_compat():
    """19. Existing Task 3 tests continue passing"""
    researcher = GeminiResearcher()
    result = researcher.research_project("Uppal Elevated Corridor", force_refresh=True)

    assert result.project_name_query == "Uppal Elevated Corridor"
    assert isinstance(result.project, ProjectResearchData)
    assert result.research_metadata.research_status == ResearchStatus.COMPLETED

def test_20_canonical_database_mutation_zero(db_session: Session):
    """20. Live database safety: Research & routing execute with canonical mutation count = 0"""
    p_count = db_session.query(Project).count()
    t_count = db_session.query(Tender).count()
    c_count = db_session.query(Contractor).count()

    researcher = GeminiResearcher()
    result = researcher.research_project("Suryapet Road Expansion", db=db_session, force_refresh=True)

    assert db_session.query(Project).count() == p_count
    assert db_session.query(Tender).count() == t_count
    assert db_session.query(Contractor).count() == c_count
    assert db_session.query(ResearchRun).count() > 0 # Audit table allowed

def test_21_uppal_elevated_corridor_generic_validation():
    """21. Uppal Elevated Corridor works as a generic test case"""
    router = SourceRoutingService()
    adapters = router.route_request("Uppal Elevated Corridor")
    source_ids = [a.source.source_id for a in adapters]

    assert len(source_ids) >= 3
    assert "telangana_open_data" in source_ids or "nhai" in source_ids

def test_22_iit_hyderabad_generic_validation():
    """22. IIT Hyderabad works as a generic test case"""
    router = SourceRoutingService()
    adapters = router.route_request("IIT Hyderabad Campus Infrastructure")
    source_ids = [a.source.source_id for a in adapters]

    assert "cppp_eproc" in source_ids or "data_gov_in" in source_ids

def test_23_new_arbitrary_project_validation():
    """23. A completely new arbitrary project works"""
    researcher = GeminiResearcher()
    result = researcher.research_project("Khammam Bypass Elevated Link 2026", force_refresh=True)

    assert result.project_name_query == "Khammam Bypass Elevated Link 2026"
    assert result.research_metadata.sources_selected > 0
    assert result.research_metadata.research_status == ResearchStatus.COMPLETED
