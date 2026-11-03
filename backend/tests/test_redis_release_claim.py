"""release_claim: libera un claim de Redis para poder reintentar un ciclo."""

import pytest

from app.config import settings
from app.core import redis_claim


@pytest.mark.asyncio
async def test_release_claim_permite_volver_a_reclamar(monkeypatch):
    held = set()

    class FakeRedis:
        async def set(self, key, value, nx=False, ex=None):
            if nx and key in held:
                return None
            held.add(key)
            return True

        async def delete(self, key):
            held.discard(key)

    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")
    monkeypatch.setattr(redis_claim, "_redis_client", FakeRedis())

    assert await redis_claim.claim_once("k", 60) is True
    assert await redis_claim.claim_once("k", 60) is False
    await redis_claim.release_claim("k")
    assert await redis_claim.claim_once("k", 60) is True
    # Liberar una clave de otro evento no toca la que sigue tomada.
    await redis_claim.release_claim("otra")
    assert await redis_claim.claim_once("k", 60) is False


@pytest.mark.asyncio
async def test_release_claim_sin_redis_o_con_redis_caido_no_lanza(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "")
    await redis_claim.release_claim("k")

    class BrokenRedis:
        async def delete(self, *a, **k):
            raise ConnectionError("redis caido")

    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")
    monkeypatch.setattr(redis_claim, "_redis_client", BrokenRedis())
    await redis_claim.release_claim("k")
