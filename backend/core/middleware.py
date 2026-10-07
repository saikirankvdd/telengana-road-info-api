import uuid
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.config import settings
from backend.api.v1.system import METRICS_DATA

logger = logging.getLogger("http_tracer")

class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique correlation request ID (X-Request-ID) to every incoming HTTP request.
    Traces duration, HTTP status, method, path, and records request metrics.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 1. Obtain or generate correlation ID
        correlation_id = request.headers.get(settings.CORRELATION_HEADER)
        if not correlation_id:
            correlation_id = f"req_{uuid.uuid4().hex[:12]}"
        
        # Attach to request state
        request.state.correlation_id = correlation_id
        
        # 2. Increment request count
        METRICS_DATA["http_requests_total"] += 1
        
        try:
            response: Response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Attach correlation header to response
            response.headers[settings.CORRELATION_HEADER] = correlation_id
            
            if response.status_code >= 400:
                METRICS_DATA["http_errors_total"] += 1
                logger.warning(
                    f"[TRACE] id={correlation_id} | method={request.method} | path={request.url.path} | "
                    f"status={response.status_code} | duration={duration_ms:.2f}ms"
                )
            else:
                logger.info(
                    f"[TRACE] id={correlation_id} | method={request.method} | path={request.url.path} | "
                    f"status={response.status_code} | duration={duration_ms:.2f}ms"
                )
                
            return response
        except Exception as exc:
            METRICS_DATA["http_errors_total"] += 1
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[TRACE_ERROR] id={correlation_id} | method={request.method} | path={request.url.path} | "
                f"error={exc} | duration={duration_ms:.2f}ms"
            )
            raise exc
