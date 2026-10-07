import time
import logging
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Request rate limits: (max_requests, window_seconds)
RATE_LIMITS = {
    "/api/v1/auth/login": (10, 60),        # Max 10 logins per minute
    "/api/v1/research/project": (15, 60),  # Max 15 research requests per minute
    "/api/v1/auth/users": (20, 60)         # Max 20 user management calls per minute
}

DEFAULT_RATE_LIMIT = (120, 60)             # Max 120 calls per minute default


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiting middleware supporting in-memory storage
    and optional Redis backend when REDIS_URL is configured.
    Prevents abuse on expensive research, login, and admin endpoints.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.client_requests: Dict[str, List[float]] = {}
        self.redis_client = None
        
        from backend.core.config import settings
        if settings.REDIS_URL:
            try:
                import redis
                self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info("Connected to Redis backend for distributed rate limiting.")
            except Exception as e:
                logger.warning(f"Failed connecting to Redis for rate limiting ({e}). Falling back to in-memory.")

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        client_ip = request.client.host if request.client else "127.0.0.1"

        # Determine rate limit for endpoint
        max_requests, window_seconds = DEFAULT_RATE_LIMIT
        for route_prefix, limit_tuple in RATE_LIMITS.items():
            if path.startswith(route_prefix):
                max_requests, window_seconds = limit_tuple
                break

        key = f"rate_limit:{client_ip}:{path}"
        now = time.time()

        # Redis-backed rate limiting path
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window_seconds)
                res = pipe.execute()
                current_count = res[1]
                if current_count >= max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
                    )
                return await call_next(request)
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Redis rate limit check error ({e}), falling back to memory.")

        # In-memory sliding window path
        timestamps = self.client_requests.get(key, [])
        valid_timestamps = [t for t in timestamps if now - t < window_seconds]

        if len(valid_timestamps) >= max_requests:
            logger.warning(f"Rate limit exceeded for client {client_ip} on path {path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
            )

        valid_timestamps.append(now)
        self.client_requests[key] = valid_timestamps

        response = await call_next(request)
        return response

