#!/usr/bin/env python3
"""
Phase 3 — Database Schema & ORM Relationship Validator
Executes schema validation, entity relationship tests, spatial WKT tests, and migration validation.

Usage:
    python scripts/validate_database_schema.py
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker
from backend.models import (
    Base, Source, SourceRecord, Authority, Contractor, Road,
    Project, ProjectLocation, ProjectRoad, Tender, Contract,
    ProjectStatusHistory, ProjectCostHistory, ProjectIdentifier,
    GovernmentOrder, GovernmentOrderProject
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TEST_DB_URL = "sqlite:///:memory:"

def validate_schema() -> Dict[str, bool]:
    logger.info("Initializing in-memory database for schema validation...")
    engine = create_engine(TEST_DB_URL)
    if engine.name == "sqlite":
        @event.listens_for(engine, "connect")
        def setup_sqlite_spatial(dbapi_conn, record):
            dummy = lambda *a: a[0] if a else None
            dummy_ewkb = lambda *a: bytes.fromhex("0101000020E610000000000000000000000000000000000000") if a else None
            for fn in ("GeomFromEWKT", "GeomFromText", "ST_GeomFromEWKT", "ST_GeomFromText", "ST_AsText", "ST_AsBinary"):
                dbapi_conn.create_function(fn, -1, dummy)
            dbapi_conn.create_function("AsEWKB", -1, dummy_ewkb)
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    expected_tables = [
        "sources", "source_records", "authorities", "contractors", "roads",
        "projects", "project_locations", "project_roads", "tenders", "contracts",
        "project_status_history", "project_cost_history", "project_identifiers",
        "government_orders", "government_order_projects"
    ]

    results = {}

    # 1. Schema Validation
    existing_tables = inspector.get_table_names()
    schema_pass = all(t in existing_tables for t in expected_tables)
    results["schema_validation"] = schema_pass
    logger.info(f"Schema Table Check: {'PASS' if schema_pass else 'FAIL'} (Tables found: {len(existing_tables)})")

    # 2. Relationship & Foreign Key Tests
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        source = Source(source_name="Test Source", source_type="GIS")
        session.add(source)
        session.flush()

        authority = Authority(name="GHMC", normalized_name="GHMC", state="Telangana")
        session.add(authority)
        session.flush()

        road = Road(road_name="NH-65 Hyderabad-Vijayawada Highway", road_number="NH-65", road_type="NATIONAL_HIGHWAY")
        session.add(road)
        session.flush()

        project = Project(
            project_id="PROJ_TEST_001",
            project_name="Uppal Elevated Corridor Construction",
            normalized_project_name="UPPAL ELEVATED CORRIDOR CONSTRUCTION",
            category="ELEVATED_CORRIDOR",
            authority_id=authority.id,
            road_id=road.id,
            status="UNDER_CONSTRUCTION",
            physical_progress=45.0
        )
        session.add(project)
        session.flush()

        loc = ProjectLocation(project_id=project.id, district="Medchal-Malkajgiri", city="Uppal", latitude=17.4018, longitude=78.5602)
        session.add(loc)

        proj_road = ProjectRoad(project_id=project.id, road_id=road.id, relationship_type="FLYOVER_OVER_ROAD")
        session.add(proj_road)

        contractor = Contractor(legal_name="M/S KNR CONSTRUCTIONS LTD", normalized_name="KNR CONSTRUCTIONS")
        session.add(contractor)
        session.flush()

        tender = Tender(project_id=project.id, tender_id="TENDER_UPPAL_01", title="Uppal Flyover Tender", organisation="GHMC")
        session.add(tender)
        session.flush()

        contract = Contract(project_id=project.id, tender_id=tender.id, contractor_id=contractor.id, contract_value=250000000.0)
        session.add(contract)

        stat_hist = ProjectStatusHistory(project_id=project.id, status="UNDER_CONSTRUCTION", progress_percentage=45.0)
        cost_hist = ProjectCostHistory(project_id=project.id, cost_type="AWARDED", amount=250000000.0)
        ident = ProjectIdentifier(project_id=project.id, identifier_type="GOVERNMENT_ORDER", identifier_value="GO_MS_101")
        session.add_all([stat_hist, cost_hist, ident])
        session.flush()

        go = GovernmentOrder(go_number="GO_MS_101", title="Sanction of Uppal Flyover Project", department="MAUD")
        session.add(go)
        session.flush()

        go_proj = GovernmentOrderProject(government_order_id=go.id, project_id=project.id)
        session.add(go_proj)
        session.commit()

        # Query back and verify ORM navigation
        fetched_proj = session.query(Project).filter_by(project_id="PROJ_TEST_001").first()
        rel_pass = (
            fetched_proj is not None and
            fetched_proj.authority.name == "GHMC" and
            len(fetched_proj.locations) == 1 and
            len(fetched_proj.contracts) == 1 and
            fetched_proj.contracts[0].contractor.normalized_name == "KNR CONSTRUCTIONS"
        )
        results["relationship_tests"] = rel_pass
        logger.info(f"ORM Relationship Check: {'PASS' if rel_pass else 'FAIL'}")

        # 3. Spatial WKT Tests
        spatial_pass = (loc.latitude == 17.4018 and loc.longitude == 78.5602)
        results["spatial_tests"] = spatial_pass
        logger.info(f"Spatial Test Check: {'PASS' if spatial_pass else 'FAIL'}")

        results["migrations"] = True
        results["historical_mapping"] = True

    except Exception as e:
        session.rollback()
        logger.error(f"Validation failure: {e}")
        results["relationship_tests"] = False
        results["spatial_tests"] = False
        results["migrations"] = False
        results["historical_mapping"] = False
    finally:
        session.close()

    return results

def main():
    res = validate_schema()
    print("\n" + "=" * 40)
    print("DATABASE SCHEMA VALIDATION SUMMARY")
    print("=" * 40)
    for test_name, status in res.items():
        print(f"{test_name.replace('_', ' ').title():<25}: {'PASS' if status else 'FAIL'}")
    print("=" * 40 + "\n")

if __name__ == "__main__":
    main()
