"""Per-client request limits for /api/v1: a sliding one-minute window, kept in memory per API process.

Writes (POST, DELETE) are limited separately from reads, which the Process view and streams make often.
"""

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings

WINDOW_SECONDS = 60.0
EXEMPT_PREFIX = "/api/v1/health/"


class RateLimiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.hits: dict[tuple, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: tuple, limit: int) -> float:
        """Record a hit; return 0 if allowed, else the seconds until the oldest hit leaves the window."""
        now = self.clock()
        with self.lock:
            hits = self.hits[key]
            while hits and now - hits[0] >= WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= limit:
                return WINDOW_SECONDS - (now - hits[0])
            hits.append(now)
            if len(self.hits) > 10_000:  # forget idle clients
                for stale in [k for k, v in self.hits.items() if not v or now - v[-1] >= WINDOW_SECONDS]:
                    del self.hits[stale]
            return 0.0


limiter = RateLimiter()


def limits_for(method: str) -> tuple[str, int]:
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write", settings.rate_limit_writes_per_minute
    return "read", settings.rate_limit_reads_per_minute


async def rate_limit(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/v1/") or path.startswith(EXEMPT_PREFIX) or request.method == "OPTIONS":
        return await call_next(request)
    kind, limit = limits_for(request.method)
    client = request.client.host if request.client else "unknown"
    wait = limiter.check((client, kind), limit)
    if wait:
        return JSONResponse(
            status_code=429,
            content={"detail": {"code": "RATE_LIMITED", "message": f"Too many requests. Try again in {math.ceil(wait)} s."}},
            headers={"Retry-After": str(math.ceil(wait))},
        )
    return await call_next(request)
