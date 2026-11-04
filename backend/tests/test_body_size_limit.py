import pytest

from app.config import settings

pytestmark = pytest.mark.asyncio


async def test_oversized_body_is_rejected_before_reaching_the_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BODY_SIZE", 100)

    # /auth/api/register es publico: si el limite no corriera, esto llegaria
    # al validator de Pydantic (y probablemente fallaria distinto, o peor,
    # se procesaria entero).
    payload = {
        "email": "test@test.com",
        "full_name": "x",
        "password": "x" * 500,
    }
    resp = await client.post("/auth/api/register", json=payload)
    assert resp.status_code == 413


async def test_normal_sized_body_is_not_affected(client):
    resp = await client.post(
        "/auth/api/login", json={"email": "nadie@test.com", "password": "x"}
    )
    # 401 (credenciales invalidas), no 413: confirma que el limite default no
    # molesta a un request normal.
    assert resp.status_code == 401
