"""
Rate Limiting / Backpressure — caps log ingestion per source.

Configurable max logs/second per source. Excess logs return 429.
"""

import logging
import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

MAX_LOGS_PER_SECOND = int(os.getenv("RATE_LIMIT_PER_SECOND", "1000"))


class RateLimitState:
    """Tracks request counts per source per second."""

    def __init__(self, max_per_second: int = MAX_LOGS_PER_SECOND):
        self.max_per_second = max_per_second
        self._counts = defaultdict(list)  # source → [timestamps]

    def is_allowed(self, source: str = "global") -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        window_start = now - 1.0  # 1-second window

        # Clean old entries
        self._counts[source] = [t for t in self._counts[source] if t > window_start]

        if len(self._counts[source]) >= self.max_per_second:
            return False

        self._counts[source].append(now)
        return True

    def get_stats(self) -> dict:
        """Get current rate limit stats."""
        now = time.time()
        window_start = now - 1.0
        stats = {}
        for source, timestamps in self._counts.items():
            current = [t for t in timestamps if t > window_start]
            stats[source] = {
                "current_rate": len(current),
                "max_rate": self.max_per_second
            }
        return stats


# Global rate limiter instance
rate_limiter = RateLimitState()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting /classify endpoint."""

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit log ingestion endpoints
        if request.url.path in ("/classify", "/upload-csv"):
            # Try to get source from request (best effort)
            source = "global"
            if request.method == "POST":
                try:
                    body = await request.body()
                    import json
                    data = json.loads(body)
                    source = data.get("source", "global") or "global"
                    # Re-inject body for downstream
                    from starlette.requests import Request as StarletteRequest
                    request._body = body
                except Exception:
                    pass

            if not rate_limiter.is_allowed(source):
                logger.warning(f"[RATE-LIMIT] Rate limit exceeded for source: {source}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for source '{source}'. Max {MAX_LOGS_PER_SECOND}/sec."
                )

        response = await call_next(request)
        return response
