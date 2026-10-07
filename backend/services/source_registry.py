import logging
from typing import Dict, List, Optional
from backend.schemas.government_source import (
    GovernmentSource,
    GovernmentSourceType,
    LegalAccessStatus,
    ProjectDomain
)
from backend.schemas.research import AuthorityLevel
from backend.adapters.base_adapter import GovernmentSourceAdapter
from backend.adapters.government_adapters import (
    GenericWebSearchAdapter,
    TelanganaOpenDataAdapter,
    GisAdapter,
    ProtectedSourceAdapter
)

logger = logging.getLogger(__name__)

class GovernmentSourceRegistry:
    """
    Centralized registry managing all registered government and external data sources and their adapters.
    No hardcoded source logic throughout the researcher.
    """
    def __init__(self):
        self._sources: Dict[str, GovernmentSource] = {}
        self._adapters: Dict[str, GovernmentSourceAdapter] = {}
        self._initialize_default_registry()

    def _initialize_default_registry(self):
        # 1. Telangana Open Data Portal
        src_tod = GovernmentSource(
            source_id="telangana_open_data",
            name="Telangana Open Data Portal",
            base_url="https://data.telangana.gov.in/api/v1",
            source_type=GovernmentSourceType.OFFICIAL_OPEN_DATA,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="IT, Electronics & Communications Dept",
            supported_domains=[
                ProjectDomain.MUNICIPAL,
                ProjectDomain.HMDA_INFRASTRUCTURE,
                ProjectDomain.STATE_HIGHWAY,
                ProjectDomain.RURAL_ROAD,
                ProjectDomain.GENERIC
            ],
            supported_data_types=["tender", "cost", "contractor", "location"],
            access_method="API",
            enabled=True,
            priority=1
        )
        self.register_source(src_tod, TelanganaOpenDataAdapter(src_tod))

        # 2. data.gov.in (Open Government Data India)
        src_datagov = GovernmentSource(
            source_id="data_gov_in",
            name="Open Government Data Portal India (data.gov.in)",
            base_url="https://api.data.gov.in",
            source_type=GovernmentSourceType.OFFICIAL_OPEN_DATA,
            authority_level=AuthorityLevel.PRIMARY,
            state="India",
            department="Ministry of Electronics & IT",
            supported_domains=[
                ProjectDomain.NATIONAL_HIGHWAY,
                ProjectDomain.CENTRAL_INSTITUTION,
                ProjectDomain.GENERIC
            ],
            supported_data_types=["tender", "cost", "project_details"],
            access_method="API",
            enabled=True,
            priority=2
        )
        self.register_source(src_datagov, GenericWebSearchAdapter(src_datagov, site_filter="data.gov.in"))

        # 3. CPPP / Central Public Procurement Portal
        src_cppp = GovernmentSource(
            source_id="cppp_eproc",
            name="Central Public Procurement Portal (CPPP / eProcure)",
            base_url="https://eprocure.gov.in/eprocure/app",
            source_type=GovernmentSourceType.PROCUREMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="India",
            department="NIC / Ministry of Finance",
            supported_domains=[
                ProjectDomain.NATIONAL_HIGHWAY,
                ProjectDomain.CENTRAL_INSTITUTION,
                ProjectDomain.MUNICIPAL,
                ProjectDomain.HMDA_INFRASTRUCTURE,
                ProjectDomain.GENERIC
            ],
            supported_data_types=["tender", "tender_id", "reference_number", "awarded_cost", "contractor"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_cppp, GenericWebSearchAdapter(src_cppp, site_filter="eprocure.gov.in"))

        # 4. NHAI (National Highways Authority of India)
        src_nhai = GovernmentSource(
            source_id="nhai",
            name="National Highways Authority of India (NHAI)",
            base_url="https://nhai.gov.in",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="India",
            department="Ministry of Road Transport & Highways",
            supported_domains=[ProjectDomain.NATIONAL_HIGHWAY],
            supported_data_types=["project_details", "cost", "length", "contractor", "status"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_nhai, GenericWebSearchAdapter(src_nhai, site_filter="nhai.gov.in"))

        # 5. MoRTH (Ministry of Road Transport & Highways)
        src_morth = GovernmentSource(
            source_id="morth",
            name="Ministry of Road Transport and Highways (MoRTH)",
            base_url="https://morth.nic.in",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="India",
            department="MoRTH",
            supported_domains=[ProjectDomain.NATIONAL_HIGHWAY, ProjectDomain.CENTRAL_INSTITUTION],
            supported_data_types=["road_number", "cost", "dpr_reference"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_morth, GenericWebSearchAdapter(src_morth, site_filter="morth.nic.in"))

        # 6. GHMC (Greater Hyderabad Municipal Corporation)
        src_ghmc = GovernmentSource(
            source_id="ghmc",
            name="Greater Hyderabad Municipal Corporation (GHMC)",
            base_url="https://www.ghmc.gov.in",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="GHMC Municipal Administration",
            supported_domains=[ProjectDomain.MUNICIPAL],
            supported_data_types=["location", "cost", "status", "contractor"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_ghmc, GenericWebSearchAdapter(src_ghmc, site_filter="ghmc.gov.in"))

        # 7. HMDA (Hyderabad Metropolitan Development Authority)
        src_hmda = GovernmentSource(
            source_id="hmda",
            name="Hyderabad Metropolitan Development Authority (HMDA)",
            base_url="https://www.hmda.gov.in",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="HMDA Urban Infrastructure",
            supported_domains=[ProjectDomain.HMDA_INFRASTRUCTURE],
            supported_data_types=["project_name", "location", "cost", "contractor"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_hmda, GenericWebSearchAdapter(src_hmda, site_filter="hmda.gov.in"))

        # 8. PMGSY / OMMAS (Pradhan Mantri Gram Sadak Yojana)
        src_pmgsy = GovernmentSource(
            source_id="pmgsy_ommas",
            name="PMGSY / OMMAS Rural Road Portal",
            base_url="https://omms.nic.in",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="Panchayati Raj & Rural Development",
            supported_domains=[ProjectDomain.RURAL_ROAD],
            supported_data_types=["road_number", "length", "cost", "contractor"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_pmgsy, GenericWebSearchAdapter(src_pmgsy, site_filter="omms.nic.in"))

        # 9. Telangana Roads & Buildings Department (R&B)
        src_rnb = GovernmentSource(
            source_id="telangana_rnb",
            name="Telangana Roads & Buildings Department (R&B)",
            base_url="https://transport.telangana.gov.in",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="Roads & Buildings",
            supported_domains=[ProjectDomain.NATIONAL_HIGHWAY, ProjectDomain.STATE_HIGHWAY, ProjectDomain.GENERIC],
            supported_data_types=["tender", "cost", "contractor", "go_number"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_rnb, GenericWebSearchAdapter(src_rnb, site_filter="telangana.gov.in"))

        # 10. Telangana Government Orders (goir.telangana.gov.in)
        src_go = GovernmentSource(
            source_id="telangana_go",
            name="Telangana Government Orders Portal (GOIR)",
            base_url="https://goir.telangana.gov.in",
            source_type=GovernmentSourceType.GOVERNMENT_ORDER_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="General Administration / Finance",
            supported_domains=[ProjectDomain.GOVERNMENT_ORDER, ProjectDomain.GENERIC],
            supported_data_types=["government_order_number", "government_order_date", "sanctioned_cost"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=1
        )
        self.register_source(src_go, GenericWebSearchAdapter(src_go, site_filter="goir.telangana.gov.in"))

        # 11. GIS Sources (TRAC GIS / Bhuvan / OSM Overpass)
        src_gis = GovernmentSource(
            source_id="gis_sources",
            name="Official Vector GIS & Remote Sensing Services (TRAC / Bhuvan / OSM)",
            base_url="http://tracgis.telangana.gov.in",
            source_type=GovernmentSourceType.OFFICIAL_GIS,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="TRAC / NRSC / OpenStreetMap",
            supported_domains=[
                ProjectDomain.NATIONAL_HIGHWAY,
                ProjectDomain.MUNICIPAL,
                ProjectDomain.HMDA_INFRASTRUCTURE,
                ProjectDomain.RURAL_ROAD,
                ProjectDomain.GENERIC
            ],
            supported_data_types=["latitude", "longitude", "geometry_wkt", "road_number", "location"],
            access_method="GIS_WMS",
            enabled=True,
            priority=1
        )
        self.register_source(src_gis, GisAdapter(src_gis))

        # 12. Secondary Reputable News Media
        src_news = GovernmentSource(
            source_id="secondary_news",
            name="Established Media & News Coverage",
            base_url="https://news.google.com",
            source_type=GovernmentSourceType.NEWS_SOURCE,
            authority_level=AuthorityLevel.SECONDARY,
            state="Telangana",
            department="Media",
            supported_domains=[ProjectDomain.GENERIC],
            supported_data_types=["status", "cost_estimate", "general_info"],
            access_method="WEB_SCRAPE",
            enabled=True,
            priority=3
        )
        self.register_source(src_news, GenericWebSearchAdapter(src_news, site_filter=None))

        # 13. Protected CAPTCHA Portal (Security Rule compliance test)
        src_protected = GovernmentSource(
            source_id="protected_captcha_portal",
            name="Protected Government System (CAPTCHA Gated)",
            base_url="https://protected.telangana.gov.in/auth",
            source_type=GovernmentSourceType.OFFICIAL_GOVERNMENT_PORTAL,
            authority_level=AuthorityLevel.PRIMARY,
            state="Telangana",
            department="Protected Registry",
            supported_domains=[ProjectDomain.GENERIC],
            supported_data_types=["confidential"],
            access_method="WEB_SCRAPE",
            enabled=False,
            priority=99,
            legal_access_status=LegalAccessStatus.CAPTCHA_PROTECTED
        )
        self.register_source(src_protected, ProtectedSourceAdapter(src_protected))

    def register_source(self, source: GovernmentSource, adapter: GovernmentSourceAdapter):
        self._sources[source.source_id] = source
        self._adapters[source.source_id] = adapter
        logger.info(f"Registered government source: {source.name} ({source.source_id})")

    def get_source(self, source_id: str) -> Optional[GovernmentSource]:
        return self._sources.get(source_id)

    def get_adapter(self, source_id: str) -> Optional[GovernmentSourceAdapter]:
        return self._adapters.get(source_id)

    def list_all_sources(self) -> List[GovernmentSource]:
        return list(self._sources.values())

    def list_all_adapters(self) -> List[GovernmentSourceAdapter]:
        return list(self._adapters.values())
