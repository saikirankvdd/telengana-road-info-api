import logging
from typing import List, Dict, Any, Optional

from backend.schemas.government_source import ProjectDomain, GovernmentSource
from backend.adapters.base_adapter import GovernmentSourceAdapter
from backend.services.source_registry import GovernmentSourceRegistry

logger = logging.getLogger(__name__)

class SourceRoutingService:
    """
    Intelligent Source Routing Service.
    Determines project domain characteristics dynamically from the research query/request
    and selects an ordered, prioritized list of relevant government source adapters.
    
    CRITICAL RULE: Routing logic is strictly generic.
    NO hardcoded project names (e.g. 'Uppal Elevated Corridor' or 'IIT Hyderabad') are used in production rules.
    """
    def __init__(self, registry: Optional[GovernmentSourceRegistry] = None):
        self.registry = registry or GovernmentSourceRegistry()

    def identify_domain(self, query: str, context: Optional[Dict[str, Any]] = None) -> ProjectDomain:
        q_upper = query.upper().strip()
        ctx_auth = (context.get("authority") or "").upper() if context else ""
        ctx_road = (context.get("road_number") or "").upper() if context else ""

        # Rule 1: Government Order Search
        if "G.O" in q_upper or "GOVERNMENT ORDER" in q_upper or "GOIR" in q_upper or "ADMINISTRATIVE SANCTION" in q_upper:
            return ProjectDomain.GOVERNMENT_ORDER

        # Rule 2: National Highway Search
        if "NH-" in q_upper or "NH " in q_upper or "NATIONAL HIGHWAY" in q_upper or "NHAI" in q_upper or "MORTH" in q_upper or "NH-" in ctx_road or "NHAI" in ctx_auth:
            return ProjectDomain.NATIONAL_HIGHWAY

        # Rule 3: Central Institution Infrastructure Search
        if any(term in q_upper for term in ["IIT", "NIT", "AIIMS", "CENTRAL UNIVERSITY", "CPWD", "IIIT", "ICRISAT"]):
            return ProjectDomain.CENTRAL_INSTITUTION

        # Rule 4: HMDA Infrastructure Search
        if "HMDA" in q_upper or "OUTER RING ROAD" in q_upper or "ORR" in q_upper or "RADIAL ROAD" in q_upper or "HMDA" in ctx_auth:
            return ProjectDomain.HMDA_INFRASTRUCTURE

        # Rule 5: GHMC Municipal Search
        if "GHMC" in q_upper or "GREATER HYDERABAD" in q_upper or "SRDP" in q_upper or "MUNICIPAL" in q_upper or "GHMC" in ctx_auth:
            return ProjectDomain.MUNICIPAL

        # Rule 6: Rural Road / PMGSY Search
        if "PMGSY" in q_upper or "OMMAS" in q_upper or "GRAM" in q_upper or "PANCHAYAT" in q_upper or "RURAL" in q_upper:
            return ProjectDomain.RURAL_ROAD

        # Rule 7: State Highway Search
        if "SH-" in q_upper or "STATE HIGHWAY" in q_upper or "R&B" in q_upper or "ROADS & BUILDINGS" in q_upper:
            return ProjectDomain.STATE_HIGHWAY

        return ProjectDomain.GENERIC

    def route_request(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[GovernmentSourceAdapter]:
        domain = self.identify_domain(query, context)
        logger.info(f"Dynamically routed project research query '{query}' to domain: {domain.value}")

        # Domain specific source ordering templates
        priority_order_map = {
            ProjectDomain.NATIONAL_HIGHWAY: [
                "nhai", "morth", "cppp_eproc", "data_gov_in", "telangana_rnb", "gis_sources", "secondary_news"
            ],
            ProjectDomain.MUNICIPAL: [
                "ghmc", "telangana_open_data", "cppp_eproc", "gis_sources", "secondary_news"
            ],
            ProjectDomain.HMDA_INFRASTRUCTURE: [
                "hmda", "telangana_open_data", "cppp_eproc", "gis_sources", "secondary_news"
            ],
            ProjectDomain.RURAL_ROAD: [
                "pmgsy_ommas", "telangana_open_data", "gis_sources", "secondary_news"
            ],
            ProjectDomain.GOVERNMENT_ORDER: [
                "telangana_go", "telangana_rnb", "telangana_open_data", "secondary_news"
            ],
            ProjectDomain.CENTRAL_INSTITUTION: [
                "cppp_eproc", "data_gov_in", "morth", "gis_sources", "secondary_news"
            ],
            ProjectDomain.STATE_HIGHWAY: [
                "telangana_rnb", "telangana_open_data", "cppp_eproc", "gis_sources", "secondary_news"
            ],
            ProjectDomain.GENERIC: [
                "telangana_open_data", "cppp_eproc", "telangana_rnb", "gis_sources", "secondary_news"
            ]
        }

        ordered_source_ids = priority_order_map.get(domain, priority_order_map[ProjectDomain.GENERIC])
        
        adapters: List[GovernmentSourceAdapter] = []
        for s_id in ordered_source_ids:
            adapter = self.registry.get_adapter(s_id)
            if adapter and adapter.is_available():
                adapters.append(adapter)

        return adapters
