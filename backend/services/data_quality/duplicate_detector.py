import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.schemas.research import ProjectResearchData
from backend.schemas.data_quality import DuplicateCandidateSummary
from backend.services.entity_resolution_service import EntityResolutionService, normalize_string

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects potential duplicate canonical projects for a researched project payload.
    Leverages EntityResolutionService matching signals without performing canonical merges.
    """

    def __init__(self, db: Session):
        self.db = db
        self.resolver = EntityResolutionService(db)

    def find_duplicate_candidates(
        self,
        project_name: str,
        project_data: ProjectResearchData
    ) -> List[DuplicateCandidateSummary]:
        candidates: List[DuplicateCandidateSummary] = []
        if not self.db:
            return candidates

        try:
            # Import mock ProjectResearchResult container to evaluate via EntityResolutionService
            from backend.schemas.research import ProjectResearchResult, ResearchMetadata
            mock_result = ProjectResearchResult(
                project_name_query=project_name,
                project=project_data,
                sources=[],
                field_verifications={},
                research_metadata=ResearchMetadata(research_status="COMPLETED")
            )

            res = self.resolver.resolve(mock_result)
            if res and res.candidate_entity_id:
                # Include best candidate if match score/confidence > 0.60
                if res.match_confidence >= 0.60:
                    candidates.append(DuplicateCandidateSummary(
                        candidate_id=res.candidate_entity_id,
                        project_name=res.candidate_project_name if hasattr(res, "candidate_project_name") and res.candidate_project_name else project_name,
                        match_score=res.match_confidence,
                        matching_signals=res.matching_signals or [],
                        conflicting_signals=res.negative_signals or []
                    ))
        except Exception as e:
            logger.warning(f"Error in DuplicateDetector duplicate search: {e}")

        return candidates
