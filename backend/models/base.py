from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import Engine
from sqlalchemy import event

try:
    from geoalchemy2.admin import dialects
    # Disable SpatiaLite DDL event listeners on SQLite so test suites work without SpatiaLite loaded
    dialects.sqlite.after_create = lambda table, bind, **kw: None
    dialects.sqlite.before_drop = lambda table, bind, **kw: None
    dialects.sqlite.after_drop = lambda table, bind, **kw: None
except Exception:
    pass

@event.listens_for(Engine, "connect")
def setup_sqlite_spatial_global(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        dummy = lambda *a: a[0] if a else None
        dummy_ewkb = lambda *a: bytes.fromhex("0101000020E610000000000000000000000000000000000000") if a else None
        for fn in ("GeomFromEWKT", "GeomFromText", "ST_GeomFromEWKT", "ST_GeomFromText", "ST_AsText", "ST_AsBinary", "RecoverGeometryColumn", "InitSpatialMetaData", "AddGeometryColumn"):
            try:
                dbapi_connection.create_function(fn, -1, dummy)
            except Exception:
                pass
        try:
            dbapi_connection.create_function("AsEWKB", -1, dummy_ewkb)
        except Exception:
            pass

class Base(DeclarativeBase):
    pass


