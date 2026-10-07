import logging
from typing import List, Dict, Any, Optional

from backend.schemas.research import AuthorityLevel, SourceType, SourceModel, CandidateValue, VerificationStatus, EvidentiaryField
from backend.schemas.government_source import FieldSourcePreference, GovernmentSourceType

logger = logging.getLogger(__name__)

class SourcePriorityService:
    """
    Encodes field-specific source preferences and enforces authority level hierarchy rules:
    PRIMARY > SECONDARY > TERTIARY
    
    If Primary and Secondary sources disagree:
    Retains both candidate values and marks status as CONFLICTING.
    """
    def __init__(self):
        self.field_preferences: Dict[str, List[GovernmentSourceType]] = {
            "tender_id": [GovernmentSourceType.PROCUREMENT_PORTAL, GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL, GovernmentSourceType.NEWS_SOURCE],
            "contractor": [GovernmentSourceType.PROCUREMENT_PORTAL, GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL, GovernmentSourceType.NEWS_SOURCE],
            "estimated_cost": [GovernmentSourceType.GOVERNMENT_ORDER_PORTAL, GovernmentSourceType.PROCUREMENT_PORTAL, GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL, GovernmentSourceType.NEWS_SOURCE],
            "awarded_cost": [GovernmentSourceType.PROCUREMENT_PORTAL, GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL],
            "project_status": [GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL, GovernmentSourceType.GOVERNMENT_ORDER_PORTAL, GovernmentSourceType.NEWS_SOURCE],
            "latitude": [GovernmentSourceType.OFFICIAL_GIS, GovernmentSourceType.OFFICIAL_OPEN_DATA],
            "longitude": [GovernmentSourceType.OFFICIAL_GIS, GovernmentSourceType.OFFICIAL_OPEN_DATA],
            "government_project_id": [GovernmentSourceType.GOVERNMENT_ORDER_PORTAL, GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL],
            "government_order_number": [GovernmentSourceType.GOVERNMENT_ORDER_PORTAL, GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL]
        }

    def rank_candidates(
        self,
        field_name: str,
        candidates: List[CandidateValue]
    ) -> List[CandidateValue]:
        if not candidates:
            return []

        def candidate_sort_key(cand: CandidateValue):
            auth_rank = {
                AuthorityLevel.PRIMARY: 1,
                AuthorityLevel.SECONDARY: 2,
                AuthorityLevel.TERTIARY: 3
            }.get(cand.source.authority_level, 3)

            pref_types = self.field_preferences.get(field_name, [])
            type_rank = 99
            for idx, p_type in enumerate(pref_types):
                if cand.source.source_type.value == p_type.value or cand.source.source_type.value.lower() == p_type.value.lower():
                    type_rank = idx
                    break

            return (auth_rank, type_rank, -cand.confidence)

        return sorted(candidates, key=candidate_sort_key)
