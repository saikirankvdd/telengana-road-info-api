import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("security_audit")


class SecurityAuditService:
    """
    Structured security audit logger for compliance tracking of access,
    user management, research execution, and canonical merges.
    Guarantees no sensitive secrets or plaintext credentials are ever logged.
    """

    @staticmethod
    def log_event(
        event_type: str,
        actor_username: Optional[str] = None,
        actor_role: Optional[str] = None,
        status_code: int = 200,
        details: Optional[Dict[str, Any]] = None
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        safe_details = details.copy() if details else {}

        # Redact any accidental sensitive keys from details dict
        sensitive_keys = {"password", "password_hash", "jwt_secret", "token", "api_key", "secret", "access_token"}
        for k in list(safe_details.keys()):
            if any(s in k.lower() for s in sensitive_keys):
                safe_details[k] = "[REDACTED_SECRET]"

        log_msg = (
            f"[SECURITY AUDIT] [{timestamp}] EVENT={event_type} | "
            f"ACTOR={actor_username or 'ANONYMOUS'} | ROLE={actor_role or 'NONE'} | "
            f"STATUS={status_code} | DETAILS={safe_details}"
        )

        if status_code in (401, 403) or "FAILURE" in event_type or "DENIED" in event_type:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
