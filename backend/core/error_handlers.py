import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from backend.core.config import settings

logger = logging.getLogger("error_handler")

def get_request_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown_request_id")

def register_exception_handlers(app):
    """Registers standard production exception handlers suppressing internal stack traces."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = get_request_id(request)
        error_code = "HTTP_ERROR"
        if exc.status_code == 401:
            error_code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            error_code = "FORBIDDEN"
        elif exc.status_code == 404:
            error_code = "NOT_FOUND"
        elif exc.status_code == 429:
            error_code = "RATE_LIMIT_EXCEEDED"

        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "detail": detail,
                "error": {
                    "code": error_code,
                    "message": detail,
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = get_request_id(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload body.",
                    "details": exc.errors(),
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id(request)
        logger.error(f"[UNHANDLED_EXCEPTION] id={req_id} | error={exc}", exc_info=settings.DEBUG)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "request_id": req_id
                }
            }
        )
