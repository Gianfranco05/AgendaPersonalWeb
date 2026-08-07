import pytest

from app.core.http_security import SlidingWindowRateLimiter, auth_rate_limiter


@pytest.mark.asyncio
async def test_security_headers_present(client):
    response = await client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "permissions-policy" in {k.lower() for k in response.headers.keys()}


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_max_attempts():
    limiter = SlidingWindowRateLimiter(max_attempts=3, window_seconds=60)
    assert await limiter.hit("1.2.3.4") == 0
    assert await limiter.hit("1.2.3.4") == 0
    assert await limiter.hit("1.2.3.4") == 0
    retry_after = await limiter.hit("1.2.3.4")
    assert retry_after >= 1
    # Other keys are unaffected
    assert await limiter.hit("5.6.7.8") == 0


@pytest.mark.asyncio
async def test_redis_limiter_falls_back_to_memory_when_redis_is_down():
    from app.core.http_security import RedisSlidingWindowRateLimiter

    limiter = RedisSlidingWindowRateLimiter(
        # Puerto cerrado a proposito: simula Redis caido.
        redis_url="redis://127.0.0.1:1/0",
        max_attempts=2,
        window_seconds=60,
    )
    # Falla abierto contra el limiter en memoria en vez de tirar la request.
    assert await limiter.hit("1.2.3.4") == 0
    assert await limiter.hit("1.2.3.4") == 0
    assert await limiter.hit("1.2.3.4") >= 1


@pytest.mark.asyncio
async def test_login_rate_limited(client, test_user, monkeypatch):
    monkeypatch.setattr(auth_rate_limiter, "max_attempts", 2)
    payload = {"email": "test@test.com", "password": "wrong-password"}
    r1 = await client.post("/auth/api/login", json=payload)
    r2 = await client.post("/auth/api/login", json=payload)
    assert r1.status_code == 401
    assert r2.status_code == 401
    r3 = await client.post("/auth/api/login", json=payload)
    assert r3.status_code == 429
    assert "retry-after" in {k.lower() for k in r3.headers.keys()}
