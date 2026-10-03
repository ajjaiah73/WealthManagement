"""In-process sliding-window rate limiting, applied as a FastAPI dependency.
Callers depend only on these dependency objects, so a shared backend (e.g. a
Redis token bucket) can replace the internals without touching route code.
For multi-replica deployments, swap in a shared store."""
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import settings


class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 120, window_seconds: int = 60, always_on: bool = False) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.always_on = always_on
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    async def __call__(self, request: Request) -> None:
        if not (self.always_on or settings.rate_limit_enabled):
            return
        key = request.client.host if request.client else "anonymous"
        now = time.monotonic()
        with self._lock:
            hits = [t for t in self._hits[key] if t > now - self.window_seconds]
            hits.append(now)
            self._hits[key] = hits
            exceeded = len(hits) > self.max_requests
        if exceeded:
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(self.window_seconds)}
            )


rate_limiter = InMemoryRateLimiter()
# Advisory runs call paid LLM APIs; cap them per client IP even when general limiting is off.
advisory_rate_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=60, always_on=True)
# Brute-force protection on the login endpoint is always on.
login_rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60, always_on=True)
