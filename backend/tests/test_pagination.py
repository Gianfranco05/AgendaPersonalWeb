import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("seed_transactions", [100], indirect=True)
async def test_pagination_returns_correct_page_size(api_auth_client, seed_transactions):
    response = await api_auth_client.get("/api/v1/finance/transactions?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 100
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("seed_transactions", [100], indirect=True)
async def test_pagination_pages_are_non_overlapping(api_auth_client, seed_transactions):
    page1 = await api_auth_client.get("/api/v1/finance/transactions?skip=0&limit=10")
    page2 = await api_auth_client.get("/api/v1/finance/transactions?skip=10&limit=10")
    assert page1.status_code == 200
    assert page2.status_code == 200
    ids1 = {t["id"] for t in page1.json()["items"]}
    ids2 = {t["id"] for t in page2.json()["items"]}
    assert ids1.isdisjoint(ids2), "Pages overlap"


@pytest.mark.asyncio
@pytest.mark.parametrize("seed_transactions", [100], indirect=True)
async def test_pagination_last_page_boundary(api_auth_client, seed_transactions):
    response = await api_auth_client.get("/api/v1/finance/transactions?skip=90&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["page"] == 10
    assert data["total"] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("seed_transactions", [100], indirect=True)
async def test_pagination_beyond_range(api_auth_client, seed_transactions):
    response = await api_auth_client.get("/api/v1/finance/transactions?skip=200&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0
    assert data["total"] == 100
