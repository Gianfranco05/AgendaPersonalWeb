import pytest

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio

BASE_KEYS = {"habits", "tasks", "notes", "finance", "fitness_nutrition", "calendar"}
PAID_KEYS = {"study", "library", "media", "work", "travel", "vehicle", "projects"}


async def test_list_modules_requires_auth(client):
    resp = await client.get("/api/v1/modules")
    assert resp.status_code == 401


async def test_new_user_owns_the_base_templates_only(api_auth_client):
    resp = await api_auth_client.get("/api/v1/modules")
    assert resp.status_code == 200
    modules = {m["key"]: m for m in resp.json()}

    assert set(modules) == BASE_KEYS | PAID_KEYS
    assert {k for k, m in modules.items() if m["is_base"]} == BASE_KEYS

    for key in BASE_KEYS:
        assert modules[key]["owned"] is True
        assert modules[key]["enabled"] is True
    for key in PAID_KEYS:
        assert modules[key]["owned"] is False
        assert modules[key]["enabled"] is False


async def test_a_purchased_template_starts_enabled(api_auth_client, db_session, test_user):
    await ModulesService(db_session).grant(test_user.id, "library")

    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["library"]["owned"] is True
    # Pagar una plantilla y no verla no tendria sentido.
    assert modules["library"]["enabled"] is True


async def test_a_purchased_template_can_be_turned_off_and_on(
    api_auth_client, db_session, test_user
):
    await ModulesService(db_session).grant(test_user.id, "study")

    resp = await api_auth_client.put("/api/v1/modules/study", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["owned"] is True

    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["study"]["enabled"] is False
    # Apagarla no la devuelve: sigue siendo suya.
    assert modules["study"]["owned"] is True

    resp = await api_auth_client.put("/api/v1/modules/study", json={"enabled": True})
    assert resp.json()["enabled"] is True


async def test_cannot_enable_a_template_that_was_not_bought(api_auth_client):
    resp = await api_auth_client.put("/api/v1/modules/study", json={"enabled": True})
    # 402: no es falta de permisos, falta pagarla.
    assert resp.status_code == 402


async def test_cannot_disable_a_base_template(api_auth_client):
    resp = await api_auth_client.put("/api/v1/modules/habits", json={"enabled": False})
    assert resp.status_code == 400


async def test_toggle_unknown_module_returns_404(api_auth_client):
    resp = await api_auth_client.put("/api/v1/modules/bogus", json={"enabled": True})
    assert resp.status_code == 404


async def test_for_sale_reflects_whether_the_price_is_configured(
    api_auth_client, monkeypatch
):
    from app.config import settings

    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["study"]["for_sale"] is False

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_MODULE_STUDY", "price_123")
    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["study"]["for_sale"] is True

    # Con Mercado Pago lo que cuenta es su precio, no el Price ID de Stripe.
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["study"]["for_sale"] is False
    monkeypatch.setattr(settings, "MP_PRICE_MODULE_STUDY", 299900)
    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["study"]["for_sale"] is True
    # Las incluidas nunca estan a la venta.
    assert modules["habits"]["for_sale"] is False


async def test_purchases_do_not_leak_between_users(api_auth_client, db_session, test_user):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    otro = User(
        email="otro@test.com",
        password_hash=hash_password("test123"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()

    await ModulesService(db_session).grant(otro.id, "media")

    modules = {m["key"]: m for m in (await api_auth_client.get("/api/v1/modules")).json()}
    assert modules["media"]["owned"] is False


async def test_granting_twice_does_not_duplicate(db_session, test_user):
    service = ModulesService(db_session)
    assert await service.grant(test_user.id, "study") is True
    assert await service.grant(test_user.id, "study") is False
    assert await service.owned_keys(test_user.id) == {"study"}


async def test_granting_an_unknown_template_is_rejected(db_session, test_user):
    assert await ModulesService(db_session).grant(test_user.id, "inventada") is False


async def test_paid_template_open_without_billing_in_dev(api_auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    monkeypatch.setattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "")
    # Dev/self-hosted sin cobro: no hay forma de comprarla, queda abierta.
    assert (await api_auth_client.get("/api/v1/study/summary")).status_code == 200


async def test_paid_template_locked_without_billing_in_production(api_auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    monkeypatch.setattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    # En prod un token vacio no puede regalar las plantillas pagas.
    assert (await api_auth_client.get("/api/v1/study/summary")).status_code == 402
