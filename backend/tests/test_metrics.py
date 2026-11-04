import pytest

from app.config import settings

pytestmark = pytest.mark.asyncio


async def test_metrics_is_open_when_no_token_configured(client):
    # Default: sin METRICS_TOKEN, dev/self-hosted detras de una red interna.
    resp = await client.get("/metrics")
    assert resp.status_code == 200


async def test_metrics_requires_the_token_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "s3cr3t")

    assert (await client.get("/metrics")).status_code == 401
    assert (
        await client.get("/metrics", headers={"Authorization": "Bearer wrong"})
    ).status_code == 401
    assert (
        await client.get("/metrics", headers={"Authorization": "Bearer s3cr3t"})
    ).status_code == 200
