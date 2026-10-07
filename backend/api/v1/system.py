import os
import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.connection import get_db
from backend.core.config import settings

logger = logging.getLogger("system_api")
router = APIRouter(tags=["System & Observability"])

# In-memory metrics counters
METRICS_DATA = {
    "http_requests_total": 0,
    "http_errors_total": 0,
    "research_runs_total": 0,
    "research_failures_total": 0,
    "merge_attempts_total": 0,
    "security_auth_failures_total": 0,
    "start_time": time.time()
}

@router.get("/ready", summary="Readiness probe evaluating database and core dependencies")
def readiness_check(db: Session = Depends(get_db)):
    """
    Evaluates DB connectivity and core configuration.
    Returns 200 OK when ready to serve traffic, 503 Service Unavailable if DB connection fails.
    """
    checks = {
        "database": False,
        "configuration": True,
        "gemini_configured": bool(settings.GEMINI_API_KEY)
    }
    
    try:
        # Test DB connection with pre-ping test query
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Readiness check failed - Database error: {e}")

    is_ready = checks["database"] and checks["configuration"]
    
    res_payload = {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "environment": settings.ENVIRONMENT
    }
    
    if is_ready:
        return res_payload
    return Response(
        content=str(res_payload),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        media_type="application/json"
    )

@router.get("/system/info", summary="Public production system information")
def system_info():
    """Returns safe, non-sensitive system version and environment metadata."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_v1_prefix": settings.API_V1_STR,
        "limits": {
            "max_research_sources": settings.MAX_RESEARCH_SOURCES,
            "max_gemini_calls_per_research": settings.MAX_GEMINI_CALLS_PER_RESEARCH,
            "research_timeout_seconds": settings.RESEARCH_TIMEOUT_SECONDS
        }
    }

@router.get("/metrics", summary="Prometheus-compatible operational metrics endpoint")
def prometheus_metrics():
    """Returns operational metrics in Prometheus text format."""
    uptime = time.time() - METRICS_DATA["start_time"]
    lines = [
        "# HELP http_requests_total Total HTTP requests processed.",
        "# TYPE http_requests_total counter",
        f"http_requests_total {METRICS_DATA['http_requests_total']}",
        "# HELP http_errors_total Total HTTP error responses.",
        "# TYPE http_errors_total counter",
        f"http_errors_total {METRICS_DATA['http_errors_total']}",
        "# HELP research_runs_total Total research executions.",
        "# TYPE research_runs_total counter",
        f"research_runs_total {METRICS_DATA['research_runs_total']}",
        "# HELP research_failures_total Total research failures.",
        "# TYPE research_failures_total counter",
        f"research_failures_total {METRICS_DATA['research_failures_total']}",
        "# HELP process_uptime_seconds Process uptime in seconds.",
        "# TYPE process_uptime_seconds gauge",
        f"process_uptime_seconds {uptime:.2f}"
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
