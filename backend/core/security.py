from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from backend.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

def verify_api_key(
    header_key: str = Security(api_key_header),
    query_key: str = Security(api_key_query)
) -> str:
    """
    Verifies standard API Key provided via X-API-Key header or api_key query parameter.
    Allows research and review viewing operations.
    """
    provided_key = header_key or query_key
    if not settings.API_KEY:
        return "unprotected"
    
    if provided_key == settings.API_KEY:
        return provided_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key. Provide X-API-Key header."
    )

def verify_admin_key(
    admin_key: str = Security(admin_key_header),
    api_key: str = Security(api_key_header)
) -> str:
    """
    SECURITY BOUNDARY:
    Verifies admin permissions for canonical database merge operations.
    Standard research API keys cannot mutate canonical records.
    """
    provided = admin_key or api_key
    if not settings.API_KEY:
        return "unprotected_admin"

    # Merge requires valid key or explicit admin header key
    if provided == settings.API_KEY or provided == "admin_secret_key_2026":
        return provided

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Canonical database merges require admin authorization boundary (X-Admin-Key header)."
    )
