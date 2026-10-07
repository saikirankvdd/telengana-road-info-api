import time
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.schemas.research import (
    ProjectResearchResult,
    ProjectResearchData,
    ResearchMetadata,
    ResearchStatus,
    SourceModel,
    SourceType,
    AuthorityLevel,
    CandidateValue,
    VerificationStatus,
    EvidentiaryField
)
from backend.schemas.government_source import LegalAccessStatus
from backend.adapters.base_adapter import GovernmentSourceAdapter
from backend.services.verification_service import VerificationService
from backend.services.gemini_extractor import GeminiExtractorService
from backend.services.search_provider import LiveSearchProvider
from backend.services.source_retriever import LiveSourceRetriever
from backend.services.source_registry import GovernmentSourceRegistry
from backend.services.source_routing_service import SourceRoutingService
from backend.services.query_generator import SourceQueryGenerator
from backend.services.source_priority_service import SourcePriorityService
from backend.models.research import ResearchRun, ProjectResearchSource, ProjectFieldEvidence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_total_results: int = 10) -> List[SourceModel]:
        pass

class SourceRetriever(ABC):
    @abstractmethod
    def fetch_content(self, source: SourceModel) -> Optional[str]:
        pass

class EvidenceExtractor(ABC):
    @abstractmethod
    def extract_evidence(
        self,
        project_name: str,
        source: SourceModel,
        raw_content: str
    ) -> Dict[str, Any]:
        pass

class GeminiEvidenceExtractorAdapter(EvidenceExtractor):
    def __init__(self, extractor_service: Optional[GeminiExtractorService] = None):
        self.service = extractor_service or GeminiExtractorService()

    def extract_evidence(
        self,
        project_name: str,
        source: SourceModel,
        raw_content: str
    ) -> Dict[str, Any]:
        return self.service.extract_from_evidence(
            project_name_query=project_name,
            source=source,
            raw_content=raw_content
        )

# ---------------------------------------------------------------------------
# GeminiResearcher Orchestrator (Task 5 Intelligent Source Routing)
# ---------------------------------------------------------------------------

class GeminiResearcher:
    def __init__(
        self,
        search_provider: Optional[SearchProvider] = None,
        source_retriever: Optional[SourceRetriever] = None,
        extractor: Optional[EvidenceExtractor] = None,
        verification_service: Optional[VerificationService] = None,
        source_registry: Optional[GovernmentSourceRegistry] = None,
        routing_service: Optional[SourceRoutingService] = None,
        query_generator: Optional[SourceQueryGenerator] = None,
        priority_service: Optional[SourcePriorityService] = None
    ):
        self.search_provider = search_provider or LiveSearchProvider()
        self.source_retriever = source_retriever or LiveSourceRetriever()
        self.extractor = extractor or GeminiEvidenceExtractorAdapter()
        self.verifier = verification_service or VerificationService()
        
        self.registry = source_registry or GovernmentSourceRegistry()
        self.router = routing_service or SourceRoutingService(self.registry)
        self.query_generator = query_generator or SourceQueryGenerator()
        self.priority_service = priority_service or SourcePriorityService()

    def check_cache(self, db: Optional[Session], project_name: str) -> Optional[ProjectResearchResult]:
        """Checks if a research run was completed within the last 24 hours in DB."""
        if not db:
            return None
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            run = db.query(ResearchRun).filter(
                ResearchRun.query_project_name == project_name,
                ResearchRun.status == ResearchStatus.COMPLETED.value,
                ResearchRun.created_at >= cutoff
            ).order_by(ResearchRun.created_at.desc()).first()

            if run and run.result_payload:
                result = ProjectResearchResult(**run.result_payload)
                result.project_id = str(run.id)
                return result
        except Exception as e:
            logger.warning(f"Error checking research cache: {e}")
        return None

    def research_project(
        self,
        project_name: str,
        initial_sources: Optional[List[SourceModel]] = None,
        db: Optional[Session] = None,
        force_refresh: bool = False,
        project_context: Optional[Dict[str, Any]] = None,
        search_adapters: Optional[List[GovernmentSourceAdapter]] = None
    ) -> ProjectResearchResult:
        start_time = time.time()

        # Check 24h Cache unless force_refresh is requested
        if not force_refresh:
            cached_result = self.check_cache(db, project_name)
            if cached_result:
                return cached_result

        # Step 1: Intelligent Source Routing
        selected_adapters = search_adapters if search_adapters is not None else self.router.route_request(project_name, project_context)
        sources_selected = len(selected_adapters)
        
        sources_attempted = 0
        sources_accessed = 0
        sources_failed = 0
        sources_not_accessible = 0

        raw_discovered_sources: List[SourceModel] = list(initial_sources) if initial_sources else []

        # Step 2: Multi-Source Querying and Gathering
        for adapter in selected_adapters:
            access_status = adapter.get_access_status()
            if access_status == LegalAccessStatus.NOT_ACCESSIBLE or access_status == LegalAccessStatus.CAPTCHA_PROTECTED:
                sources_not_accessible += 1
                logger.info(f"Skipping inaccessible source {adapter.source.name} (Status: {access_status.value})")
                continue

            sources_attempted += 1
            queries = self.query_generator.generate_queries(
                project_name=project_name,
                context=project_context,
                source_id=adapter.source.source_id
            )

            adapter_success = False
            for q in queries:
                try:
                    res = adapter.search(q, project_context=project_context, max_results=3)
                    if res:
                        raw_discovered_sources.extend(res)
                        adapter_success = True
                        break # Successfully retrieved results for top query
                except Exception as src_err:
                    logger.warning(f"Source adapter {adapter.source.name} search error on query '{q}': {src_err}")
            
            if not adapter_success:
                # Fall back to global search provider if adapter returns 0 results or fails
                try:
                    global_res = self.search_provider.search(f"{project_name} {adapter.source.name}", max_total_results=2)
                    if global_res:
                        raw_discovered_sources.extend(global_res)
                    else:
                        sources_failed += 1
                except Exception as g_err:
                    sources_failed += 1
                    logger.warning(f"Global fallback search error for {adapter.source.name}: {g_err}")

        # Step 3: Source & Content Deduplication (by URL & content checksum)
        seen_urls = set()
        seen_hashes = set()
        sources: List[SourceModel] = []

        for s in raw_discovered_sources:
            norm_url = (s.source_url or s.source_name).strip().lower()
            content_hash = hashlib.md5((s.evidence_text or s.title or norm_url).encode("utf-8")).hexdigest()

            if norm_url not in seen_urls and content_hash not in seen_hashes:
                seen_urls.add(norm_url)
                seen_hashes.add(content_hash)
                sources.append(s)

        source_results_found = len(sources)
        field_candidates: Dict[str, List[CandidateValue]] = {}
        sources_used = 0

        # Step 4: Evidence Extraction from Accessible Sources
        for source in sources:
            raw_text = self.source_retriever.fetch_content(source)
            if not raw_text:
                continue

            sources_accessed += 1
            sources_used += 1

            try:
                extracted = self.extractor.extract_evidence(
                    project_name=project_name,
                    source=source,
                    raw_content=raw_text
                )
            except Exception as ext_err:
                logger.warning(f"Evidence extraction error for source {source.source_name}: {ext_err}")
                extracted = {}

            for field_name, item in extracted.items():
                if field_name not in field_candidates:
                    field_candidates[field_name] = []

                if isinstance(item, dict):
                    val = item.get("value")
                    snippet = item.get("evidence_snippet")
                    conf = item.get("confidence", 0.5)
                else:
                    val = getattr(item, "value", None) if hasattr(item, "value") else item
                    snippet = getattr(item, "evidence_snippet", None) if hasattr(item, "evidence_snippet") else None
                    conf = getattr(item, "confidence", 0.5) if hasattr(item, "confidence") else 0.5

                field_candidates[field_name].append(
                    CandidateValue(
                        value=val,
                        source=source,
                        confidence=conf,
                        evidence_snippet=snippet
                    )
                )

        # Step 5: Field-Specific Source Preference Ranking & Verification
        research_data = ProjectResearchData()
        field_verifications: Dict[str, VerificationStatus] = {}

        fields_requested = len(ProjectResearchData.model_fields)
        fields_found = 0
        fields_verified = 0
        fields_unverified = 0
        fields_not_found = 0
        conflicts_found = 0

        for field_name in ProjectResearchData.model_fields.keys():
            raw_candidates = field_candidates.get(field_name, [])
            
            # Apply source priority ranking (PRIMARY > SECONDARY > TERTIARY)
            ranked_candidates = self.priority_service.rank_candidates(field_name, raw_candidates)
            
            verified_field = self.verifier.verify_field(field_name, ranked_candidates)
            setattr(research_data, field_name, verified_field)

            field_verifications[field_name] = verified_field.verification_status

            if verified_field.verification_status == VerificationStatus.NOT_FOUND:
                fields_not_found += 1
            else:
                fields_found += 1

            if verified_field.verification_status == VerificationStatus.VERIFIED:
                fields_verified += 1
            elif verified_field.verification_status in (VerificationStatus.UNVERIFIED, VerificationStatus.PARTIALLY_VERIFIED):
                fields_unverified += 1
            elif verified_field.verification_status == VerificationStatus.CONFLICTING:
                conflicts_found += 1

        duration = round(time.time() - start_time, 4)
        status = ResearchStatus.COMPLETED

        metadata = ResearchMetadata(
            searched_at=datetime.now(timezone.utc).isoformat(),
            research_duration=duration,
            sources_checked=sources_selected,
            sources_successfully_accessed=sources_accessed,
            sources_selected=sources_selected,
            sources_attempted=sources_attempted,
            sources_accessed=sources_accessed,
            sources_failed=sources_failed,
            sources_not_accessible=sources_not_accessible,
            source_results_found=source_results_found,
            source_results_used=sources_used,
            fields_requested=fields_requested,
            fields_found=fields_found,
            fields_verified=fields_verified,
            fields_unverified=fields_unverified,
            fields_not_found=fields_not_found,
            conflicts_found=conflicts_found,
            research_status=status
        )

        result = ProjectResearchResult(
            project_name_query=project_name,
            project=research_data,
            sources=sources,
            field_verifications=field_verifications,
            research_metadata=metadata
        )

        # Step 6: Persist Audit Trail cleanly into research tables (0 canonical DB mutations)
        if db:
            run_id = self.persist_research_audit_trail(db, result)
            result.project_id = str(run_id)

        return result

    def persist_research_audit_trail(self, db: Session, result: ProjectResearchResult) -> int:
        """
        DATABASE SAFETY:
        Persists research audit trail exclusively into:
        - research_runs
        - project_research_sources
        - project_field_evidences
        Does NOT alter historical canonical tables (projects, tenders, contracts, contractors, etc.).
        """
        try:
            run = ResearchRun(
                query_project_name=result.project_name_query,
                status=result.research_metadata.research_status.value,
                duration_seconds=result.research_metadata.research_duration,
                sources_checked=result.research_metadata.sources_checked,
                sources_accessed=result.research_metadata.sources_successfully_accessed,
                fields_found=result.research_metadata.fields_found,
                fields_verified=result.research_metadata.fields_verified,
                conflicts_found=result.research_metadata.conflicts_found,
                result_payload=result.model_dump()
            )
            db.add(run)
            db.flush()  # Generate run.id

            source_db_map = {}
            for src in result.sources:
                db_src = ProjectResearchSource(
                    research_run_id=run.id,
                    source_name=src.source_name,
                    source_url=src.source_url,
                    source_type=src.source_type.value,
                    authority_level=src.authority_level.value,
                    publisher=src.publisher,
                    title=src.title,
                    evidence_text=src.evidence_text,
                    page=getattr(src, "page", None)
                )
                db.add(db_src)
                db.flush()
                if src.source_id:
                    source_db_map[src.source_id] = db_src.id

            for field_name, verified_field in result.project:
                field_obj = getattr(result.project, field_name, None)
                if isinstance(field_obj, EvidentiaryField):
                    val_str = str(field_obj.value) if field_obj.value is not None else None
                    primary_src_id = None
                    if field_obj.sources and field_obj.sources[0].source_id:
                        primary_src_id = source_db_map.get(field_obj.sources[0].source_id)

                    db_ev = ProjectFieldEvidence(
                        research_run_id=run.id,
                        source_id=primary_src_id,
                        field_name=field_name,
                        extracted_value=val_str,
                        verification_status=field_obj.verification_status.value,
                        confidence=field_obj.confidence,
                        evidence_snippet=field_obj.evidence_text
                    )
                    db.add(db_ev)

            db.commit()
            return run.id

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist research audit trail: {e}")
            raise e
