import pytest

pytestmark = pytest.mark.asyncio


async def test_list_modules_requires_auth(client):
    resp = await client.get("/api/v1/modules")
    assert resp.status_code == 401


async def test_new_user_has_base_modules_on_and_new_modules_off(api_auth_client):
    resp = await api_auth_client.get("/api/v1/modules")
    assert resp.status_code == 200
    modules = resp.json()

    by_key = {m["key"]: m for m in modules}
    assert len(modules) == 9

    base_keys = {"habits", "notes", "finance", "fitness_nutrition", "calendar"}
    new_keys = {"study", "work", "vehicle", "projects"}
    assert {k for k, m in by_key.items() if m["is_base"]} == base_keys
    assert {k for k, m in by_key.items() if not m["is_base"]} == new_keys

    for key in base_keys:
        assert by_key[key]["enabled"] is True
    for key in new_keys:
        assert by_key[key]["enabled"] is False


async def test_toggle_new_module_on_and_off(api_auth_client):
    resp = await api_auth_client.put("/api/v1/modules/study", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json() == {
        "key": "study",
        "label": "Estudio & Universidad",
        "description": "Materias, exámenes y promedio",
        "icon": "school",
        "is_base": False,
        "enabled": True,
    }

    listed = await api_auth_client.get("/api/v1/modules")
    study = next(m for m in listed.json() if m["key"] == "study")
    assert study["enabled"] is True

    resp = await api_auth_client.put("/api/v1/modules/study", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


async def test_cannot_toggle_base_module(api_auth_client):
    resp = await api_auth_client.put("/api/v1/modules/habits", json={"enabled": False})
    assert resp.status_code == 400


async def test_toggle_unknown_module_returns_404(api_auth_client):
    resp = await api_auth_client.put("/api/v1/modules/bogus", json={"enabled": True})
    assert resp.status_code == 404


async def test_toggling_a_module_does_not_affect_other_users(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    other = User(
        email="other@test.com",
        password_hash=hash_password("test123"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(other)
    await db_session.commit()

    await api_auth_client.put("/api/v1/modules/work", json={"enabled": True})

    from httpx import AsyncClient, ASGITransport
    from app.main import app

    # `app` sigue teniendo el override de get_db activo (lo puso la fixture
    # `client`), asi que este segundo AsyncClient ya comparte el mismo db_session.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        login = await other_client.post(
            "/auth/api/login", json={"email": "other@test.com", "password": "test123"}
        )
        assert login.status_code == 200
        modules = (await other_client.get("/api/v1/modules")).json()
        work = next(m for m in modules if m["key"] == "work")
        assert work["enabled"] is False
