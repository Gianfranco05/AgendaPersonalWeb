import pytest

ENDPOINTS = [
    ("GET", "/api/v1/finance/summary"),
    ("GET", "/api/v1/finance/transactions"),
    ("POST", "/api/v1/finance/transactions"),
    ("PUT", "/api/v1/finance/transactions/nonexistent-id"),
    ("DELETE", "/api/v1/finance/transactions/nonexistent-id"),
    ("GET", "/api/v1/finance/categories"),
    ("GET", "/api/v1/finance/investments"),
    ("POST", "/api/v1/finance/investments"),
    ("GET", "/api/v1/finance/investments/summary"),
    ("GET", "/api/v1/finance/investments/nonexistent-id"),
    ("PUT", "/api/v1/finance/investments/nonexistent-id"),
    ("DELETE", "/api/v1/finance/investments/nonexistent-id"),
    ("GET", "/api/v1/finance/net-worth"),
    ("GET", "/api/v1/notes"),
    ("POST", "/api/v1/notes"),
    ("PUT", "/api/v1/notes/nonexistent-id"),
    ("DELETE", "/api/v1/notes/nonexistent-id"),
    ("GET", "/api/v1/notes/tags"),
    ("GET", "/api/v1/events"),
    ("POST", "/api/v1/events"),
    ("PUT", "/api/v1/events/nonexistent-id"),
    ("DELETE", "/api/v1/events/nonexistent-id"),
    ("GET", "/api/v1/goals"),
    ("POST", "/api/v1/goals"),
    ("PUT", "/api/v1/goals/nonexistent-id/checkin"),
    ("GET", "/api/v1/settings"),
    ("PUT", "/api/v1/settings"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ENDPOINTS)
async def test_api_endpoint_returns_401_without_cookie(client, method, path):
    response = await client.request(method, path)
    assert response.status_code == 401, f"{method} {path} returned {response.status_code}, expected 401"
