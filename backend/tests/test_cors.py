import pytest

ORIGIN = "http://localhost:5173"


@pytest.mark.asyncio
async def test_cors_header_present(client):
    response = await client.get("/health", headers={"Origin": ORIGIN})
    headers = {k.lower(): v for k, v in response.headers.items()}
    assert "access-control-allow-origin" in headers


@pytest.mark.asyncio
async def test_cors_allow_origin_matches(client):
    response = await client.get("/health", headers={"Origin": ORIGIN})
    cors = response.headers.get("access-control-allow-origin", "").lower()
    assert cors == ORIGIN or cors == "*"


@pytest.mark.asyncio
async def test_cors_preflight(client):
    response = await client.options(
        "/api/v1/finance/transactions",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin", "").lower() == ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_disallowed_origin_gets_no_cors_header(client):
    response = await client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in {
        k.lower(): v for k, v in response.headers.items()
    }
