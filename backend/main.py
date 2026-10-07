import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.config import settings
from backend.core.security import verify_api_key
from backend.core.rate_limiter import RateLimiterMiddleware
from sqlalchemy.orm import Session
from backend.database.connection import engine, get_db
from backend.models.base import Base
from backend.api.v1 import api_v1_router
from scripts.seed_data import seed_initial_data

from backend.core.middleware import RequestCorrelationMiddleware
from backend.core.error_handlers import register_exception_handlers
from backend.api.v1.system import readiness_check, prometheus_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("telangana_road_api")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info("Seeding initial proof-of-concept datasets...")
    seed_initial_data()
    logger.info("Application startup completed successfully.")
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Register exception handlers
register_exception_handlers(app)

# Security, Correlation & Rate Limiting Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestCorrelationMiddleware)

cors_setting = getattr(settings, "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [o.strip() for o in cors_setting.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health Probe"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/ready", tags=["Health Probe"])
def top_readiness(db: Session = Depends(get_db)):
    return readiness_check(db)

@app.get("/metrics", tags=["Metrics"])
def top_metrics():
    return prometheus_metrics()

# Include API v1 router
app.include_router(
    api_v1_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)]
)


