"""HTTP security: security headers middleware and rate limiting for auth endpoints."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        if settings.CONTENT_SECURITY_POLICY and "text/html" in response.headers.get(
            "content-type", ""
        ):
            response.headers.setdefault(
                "Content-Security-Policy", settings.CONTENT_SECURITY_POLICY
            )
        return response


class SlidingWindowRateLimiter:
    """In-memory sliding window limiter. Per-process only — enough for a
    single-instance deployment; swap for Redis if the app scales horizontally."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> int:
        """Register an attempt. Returns 0 if allowed, or seconds until retry."""
        now = time.monotonic()
        window = self._hits[key]
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.max_attempts:
            return max(1, int(window[0] + self.window_seconds - now))
        window.append(now)
        return 0

    def reset(self) -> None:
        self._hits.clear()


auth_rate_limiter = SlidingWindowRateLimiter(
    max_attempts=settings.RATE_LIMIT_MAX_ATTEMPTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


async def rate_limit_auth(request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    client_ip = request.client.host if request.client else "unknown"
    retry_after = auth_rate_limiter.hit(client_ip)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Probá de nuevo en unos minutos.",
            headers={"Retry-After": str(retry_after)},
        )
