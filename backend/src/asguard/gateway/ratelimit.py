"""In-memory sliding-window rate limiter (per application).

Single-process MVP: good enough for one ASGuard instance. For multi-instance
deployments, back this interface with Redis (documented extension point).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit_per_minute: int) -> bool:
        if limit_per_minute <= 0:
            return True
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= limit_per_minute:
            return False
        window.append(now)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)
