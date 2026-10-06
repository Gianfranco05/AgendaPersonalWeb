"""HTTP security: security headers middleware and rate limiting for auth endpoints."""
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)


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


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rechaza requests con body mas grande que `MAX_REQUEST_BODY_SIZE`.

    Chequea el header Content-Length antes de que cualquier endpoint parsee
    el body: sin esto, un JSON de varios MB (o GB) en cualquier campo de
    texto libre — incluido /auth/register, que es publico — se procesa
    entero antes de que un validator de Pydantic tenga chance de rechazarlo.
    Un cliente que omita Content-Length y mande el body chunked se escapa de
    este check; la defensa de fondo para ese caso es el limite de body de
    nginx delante del proceso (`client_max_body_size`), no este middleware.
    """

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = None
            if size is not None and size > settings.MAX_REQUEST_BODY_SIZE:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return await call_next(request)


class SlidingWindowRateLimiter:
    """In-memory sliding window limiter. Per-process only — enough for a
    single-instance deployment; see RedisSlidingWindowRateLimiter for scale-out."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def hit(self, key: str) -> int:
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


# Ventana deslizante atomica en un ZSET: recorta lo viejo, cuenta, y agrega solo
# si hay lugar. Va en Lua porque hacerlo en varios round-trips deja una carrera
# donde N instancias pasan el limite a la vez.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_attempts = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
if redis.call('ZCARD', key) >= max_attempts then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  return math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window))
return 0
"""


class RedisSlidingWindowRateLimiter:
    """Sliding window compartido entre instancias.

    Si Redis no responde cae al limiter en memoria en vez de tirar la request:
    un problema de infraestructura no deberia dejar a nadie sin poder loguearse,
    y el fallback conserva al menos el limite por proceso.
    """

    def __init__(self, redis_url: str, max_attempts: int, window_seconds: int):
        self.redis_url = redis_url
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._client = None
        self._script = None
        self._fallback = SlidingWindowRateLimiter(max_attempts, window_seconds)

    async def _ensure_client(self):
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            self._script = self._client.register_script(_SLIDING_WINDOW_LUA)
        return self._client

    async def hit(self, key: str) -> int:
        try:
            await self._ensure_client()
            result = await self._script(
                keys=[f"ratelimit:{key}"],
                args=[
                    time.time(),
                    self.window_seconds,
                    self.max_attempts,
                    uuid.uuid4().hex,
                ],
            )
            return int(result)
        except Exception:
            logger.warning(
                "Rate limiter: Redis no disponible, usando limiter en memoria",
                exc_info=True,
            )
            self._client = None
            self._script = None
            return await self._fallback.hit(key)

    def reset(self) -> None:
        self._fallback.reset()


def _build_rate_limiter(max_attempts: int, window_seconds: int):
    if settings.REDIS_URL:
        return RedisSlidingWindowRateLimiter(
            redis_url=settings.REDIS_URL,
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )
    return SlidingWindowRateLimiter(max_attempts=max_attempts, window_seconds=window_seconds)


auth_rate_limiter = _build_rate_limiter(
    settings.RATE_LIMIT_MAX_ATTEMPTS, settings.RATE_LIMIT_WINDOW_SECONDS
)
# Bucket separado del de auth: mezclar intentos de login fallidos con
# checkouts de billing haria que lo uno bloquee lo otro sin motivo. La
# ventana es mas laxa (nadie compra 10 plantillas en 5 min de uso real) y la
# key es el user_id, no la IP — es una accion autenticada, y por IP
# castigaria a cualquiera detras del mismo NAT/red corporativa que el
# usuario.
billing_rate_limiter = _build_rate_limiter(max_attempts=10, window_seconds=300)
# Boton de arrepentimiento: es publico (sin login), asi que la key es la IP.
# Mas estricto que el de auth: cada pedido dispara un mail y un aviso al
# operador, y una persona real manda uno, quizas un par si se equivoco.
withdrawal_rate_limiter = _build_rate_limiter(max_attempts=5, window_seconds=3600)


async def rate_limit_auth(request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    client_ip = request.client.host if request.client else "unknown"
    retry_after = await auth_rate_limiter.hit(client_ip)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Probá de nuevo en unos minutos.",
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limit_billing(
    current_user=Depends(get_current_user),
) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    retry_after = await billing_rate_limiter.hit(str(current_user.id))
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Probá de nuevo en unos minutos.",
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limit_withdrawal(request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    client_ip = request.client.host if request.client else "unknown"
    retry_after = await withdrawal_rate_limiter.hit(client_ip)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Probá de nuevo en unos minutos.",
            headers={"Retry-After": str(retry_after)},
        )
