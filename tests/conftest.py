import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.database.connection as db_conn
from backend.models.base import Base
from backend.core.security import verify_api_key
from scripts.seed_data import seed_initial_data

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

@event.listens_for(engine, "connect")
def setup_sqlite_spatial(dbapi_conn, record):
    dummy = lambda *a: a[0] if a else None
    dummy_ewkb = lambda *a: bytes.fromhex("0101000020E610000000000000000000000000000000000000") if a else None
    for fn in ("GeomFromEWKT", "GeomFromText", "ST_GeomFromEWKT", "ST_GeomFromText", "ST_AsText", "ST_AsBinary"):
        dbapi_conn.create_function(fn, -1, dummy)
    dbapi_conn.create_function("AsEWKB", -1, dummy_ewkb)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database module's engine and SessionLocal so lifespan & routes use test db
db_conn.engine = engine
db_conn.SessionLocal = TestingSessionLocal

from backend.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_initial_data(db=db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_verify_api_key():
    return "test_ok"

app.dependency_overrides[db_conn.get_db] = override_get_db
app.dependency_overrides[verify_api_key] = override_verify_api_key

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
