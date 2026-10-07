import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from backend.schemas.government_source import GovernmentSource, LegalAccessStatus, GovernmentSourceType
from backend.schemas.research import SourceModel, SourceType, AuthorityLevel

logger = logging.getLogger(__name__)

class GovernmentSourceAdapter(ABC):
    """
    Abstract Base Adapter for all registered government & permitted external sources.
    Standardizes searching, retrieval, status checking, and authority level classification.
    """
    def __init__(self, source: GovernmentSource):
        self.source = source

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if source endpoint is reachable and enabled."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        project_context: Optional[Dict[str, Any]] = None,
        max_results: int = 5
    ) -> List[SourceModel]:
        """Performs search on source and returns candidate SourceModel objects."""
        pass

    @abstractmethod
    def retrieve(self, source_model: SourceModel) -> Optional[str]:
        """Fetches raw text content from the source."""
        pass

    def get_access_status(self) -> LegalAccessStatus:
        """Returns legal/technical accessibility status of the source."""
        if not self.source.enabled:
            return LegalAccessStatus.NOT_ACCESSIBLE
        return self.source.legal_access_status

    def classify_source(self) -> AuthorityLevel:
        """Returns authority level (PRIMARY, SECONDARY, TERTIARY)."""
        return self.source.authority_level
