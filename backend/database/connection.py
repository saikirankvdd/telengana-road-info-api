from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.core.config import settings

# SQLite needs connect_args for multithreading in dev/tests
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

# Engine options
engine_kwargs = {
    "connect_args": connect_args,
    "echo": False,
    "pool_pre_ping": True,
}

if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

