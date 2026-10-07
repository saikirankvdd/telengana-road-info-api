import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal, engine
from backend.models.base import Base
from backend.models.source import Source
from backend.models.authority import Authority

logger = logging.getLogger(__name__)

def seed_initial_data(db: Session | None = None):
    """
    Seeds ONLY base authority master records and source configurations.
    Does NOT insert hardcoded project facts (e.g. costs, contractors, progress).
    All project records must be dynamically discovered and normalized from real connected data sources.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Create tables if not exist
        Base.metadata.create_all(bind=engine)

        # Check if source master configuration is already seeded
        if db.query(Source).first():
            logger.info("Source metadata and authority registry already initialized.")
            return

        logger.info("Initializing base source registries and government authority records...")

        # 1. Official Data Sources Provenance Records
        source_trac_gis = Source(
            source_name="Telangana State Remote Sensing Applications Centre (TRAC GIS)",
            source_type="TELANGANA_GIS",
            source_url="http://tracgis.telangana.gov.in/arcgis/rest/services",
            retrieved_at=datetime.now(timezone.utc),
            source_record_id="TRAC_GIS_SERVICES_DIR"
        )
        source_bhuvan_gis = Source(
            source_name="ISRO NRSC Bhuvan Telangana Geoportal",
            source_type="BHUVAN_GIS",
            source_url="https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms",
            retrieved_at=datetime.now(timezone.utc),
            source_record_id="BHUVAN_TG_WMS_LAYER"
        )
        source_open_gis = Source(
            source_name="OpenSpatial Vector Data (Telangana Road Infrastructure)",
            source_type="OPEN_VECTOR_GIS",
            source_url="https://overpass-api.de/api/interpreter",
            retrieved_at=datetime.now(timezone.utc),
            source_record_id="OSM_TG_ROAD_FEATURES"
        )
        source_open_data = Source(
            source_name="Telangana Open Data Portal",
            source_type="TELANGANA_OPEN_DATA",
            source_url="https://data.telangana.gov.in/api/v1",
            retrieved_at=datetime.now(timezone.utc),
            source_record_id="TOD_OPEN_DATA_PORTAL"
        )
        source_eproc = Source(
            source_name="Telangana e-Procurement Portal",
            source_type="EPROCUREMENT",
            source_url="https://tender.telangana.gov.in/public",
            retrieved_at=datetime.now(timezone.utc),
            source_record_id="EPROC_PUBLIC_PORTAL"
        )
        db.add_all([source_trac_gis, source_bhuvan_gis, source_open_gis, source_open_data, source_eproc])
        db.flush()

        # 2. Government Authorities Master Registry
        auth_morth = Authority(
            name="Ministry of Road Transport and Highways (MoRTH) / NHAI",
            authority_type="Central Ministry",
            state="Central / All India",
            contact_email="ro.hyderabad@nhai.org",
            contact_phone="040-23204991",
            official_url="https://nhai.gov.in",
            source_url="https://morth.nic.in"
        )
        auth_rnb = Authority(
            name="Telangana Roads & Buildings Department (R&B)",
            authority_type="State Department",
            state="Telangana",
            district="Hyderabad",
            contact_email="einc-rn-hyderabad@telangana.gov.in",
            contact_phone="040-23390111",
            official_url="https://transport.telangana.gov.in",
            source_url="https://telangana.gov.in"
        )
        auth_ghmc = Authority(
            name="Greater Hyderabad Municipal Corporation (GHMC)",
            authority_type="Local Body",
            state="Telangana",
            district="Hyderabad",
            contact_email="commissioner-ghmc@telangana.gov.in",
            contact_phone="040-21111111",
            official_url="https://www.ghmc.gov.in",
            source_url="https://www.ghmc.gov.in"
        )
        auth_hmda = Authority(
            name="Hyderabad Metropolitan Development Authority (HMDA)",
            authority_type="Urban Authority",
            state="Telangana",
            district="Hyderabad",
            contact_email="commissioner@hmda.gov.in",
            contact_phone="040-27003311",
            official_url="https://www.hmda.gov.in",
            source_url="https://www.hmda.gov.in"
        )
        db.add_all([auth_morth, auth_rnb, auth_ghmc, auth_hmda])

        db.commit()
        logger.info("Successfully initialized source configurations and authority master records.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding base infrastructure records: {e}")
    finally:
        if should_close:
            db.close()

if __name__ == "__main__":
    seed_initial_data()
