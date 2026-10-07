import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import (
    Base, Source, Authority, Contractor, Road, Project, ProjectLocation,
    ProjectRoad, Tender, Contract, ProjectStatusHistory, ProjectCostHistory
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_database_schema_creation(db_session):
    source = Source(source_name="Telangana GIS", source_type="GIS", official=True)
    db_session.add(source)
    db_session.flush()

    authority = Authority(name="GHMC", normalized_name="GHMC", authority_type="MUNICIPAL_CORPORATION")
    db_session.add(authority)
    db_session.flush()

    road = Road(road_name="NH-163 Uppal Corridor", road_number="NH-163", road_type="NATIONAL_HIGHWAY")
    db_session.add(road)
    db_session.flush()

    project = Project(
        project_id="PROJ_UPPAL_001",
        project_name="Construction of Uppal Elevated Corridor",
        category="ELEVATED_CORRIDOR",
        authority_id=authority.id,
        road_id=road.id,
        status="UNDER_CONSTRUCTION"
    )
    db_session.add(project)
    db_session.flush()

    assert project.id is not None
    assert project.authority.name == "GHMC"
    assert project.road.road_name == "NH-163 Uppal Corridor"

def test_project_contractor_relationship(db_session):
    contractor = Contractor(legal_name="M/S KNR CONSTRUCTIONS LTD", normalized_name="KNR CONSTRUCTIONS")
    db_session.add(contractor)
    db_session.flush()

    project = Project(project_id="P1", project_name="Road Widening")
    db_session.add(project)
    db_session.flush()

    contract = Contract(project_id=project.id, contractor_id=contractor.id, contract_value=15000000.0)
    db_session.add(contract)
    db_session.flush()

    fetched = db_session.query(Project).filter_by(project_id="P1").first()
    assert len(fetched.contracts) == 1
    assert fetched.contracts[0].contractor.normalized_name == "KNR CONSTRUCTIONS"
    assert fetched.contracts[0].contract_value == 15000000.0
