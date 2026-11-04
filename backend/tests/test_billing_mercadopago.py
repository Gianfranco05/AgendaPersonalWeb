import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.config import settings
from app.modules.billing import mercadopago
from app.modules.modulos.models import ModulePurchase
from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio

WEBHOOK_SECRET = "mp_webhook_secret_test"
WEBHOOK_URL = "/api/v1/billing/webhook/mercadopago"


class FakeMercadoPago:
    """API de Mercado Pago de mentira, servida por httpx.MockTransport.

    Se mockea el transporte y no create_preference/get_payment para que el
    test cubra tambien la URL, el metodo, el Bearer y el JSON que se mandan.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.payments: dict[str, dict] = {}
        self.fail_with: int | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": "boom"})
        if request.method == "POST" and request.url.path == "/checkout/preferences":
            return httpx.Response(
                201,
                json={
                    "id": "pref_123",
                    "init_point": "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=pref_123",
                },
            )
        if request.method == "GET" and request.url.path.startswith("/v1/payments/"):
            payment = self.payments.get(request.url.path.rsplit("/", 1)[-1])
            if payment is None:
                return httpx.Response(404, json={"message": "Payment not found"})
            return httpx.Response(200, json=payment)
        return httpx.Response(404)

    def preference_payload(self) -> dict:
        (req,) = [r for r in self.requests if r.url.path == "/checkout/preferences"]
        return json.loads(req.content)


@pytest.fixture
def fake_mp(monkeypatch):
    fake = FakeMercadoPago()

    def _client():
        return httpx.AsyncClient(
            base_url=mercadopago.MP_API_BASE,
            transport=httpx.MockTransport(fake.handler),
            headers={"Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"},
        )

    monkeypatch.setattr(mercadopago, "_client", _client)
    return fake


@pytest_asyncio.fixture
async def mp_enabled(monkeypatch, fake_mp):
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    monkeypatch.setattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "APP_USR-test-token")
    monkeypatch.setattr(settings, "MERCADOPAGO_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr(settings, "BILLING_CURRENCY", "ARS")
    monkeypatch.setattr(settings, "MP_PRICE_MODULE_STUDY", 299900)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://cancen.example.com")
    return fake_mp


def _payment(
    payment_id: str = "1234567890",
    user_id: str | None = None,
    module_key: str = "study",
    status: str = "approved",
    amount: float = 2999.0,
) -> dict:
    return {
        "id": int(payment_id),
        "status": status,
        "transaction_amount": amount,
        "currency_id": "ARS",
        "external_reference": f"{user_id}:{module_key}" if user_id else None,
        "metadata": {"user_id": user_id, "module_key": module_key} if user_id else {},
    }


def _signed_headers(data_id: str, request_id: str = "req-abc-123", ts: str = "1704908010") -> dict:
    """Firma como lo hace Mercado Pago, para no mockear verify_signature."""
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {
        "x-signature": f"ts={ts},v1={v1}",
        "x-request-id": request_id,
        "Content-Type": "application/json",
    }


async def _notify(client, data_id: str, type_: str = "payment", headers: dict | None = None):
    body = json.dumps({"action": "payment.updated", "type": type_, "data": {"id": data_id}})
    return await client.post(
        WEBHOOK_URL,
        params={"data.id": data_id, "type": type_},
        content=body,
        headers=_signed_headers(data_id) if headers is None else headers,
    )


# ── Config ───────────────────────────────────────────────────────────────────

async def test_billing_enabled_follows_the_active_provider(monkeypatch):
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "")
    # Tener Stripe cargado no habilita el cobro si el proveedor activo es MP.
    assert settings.billing_enabled is False

    monkeypatch.setattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "APP_USR-x")
    assert settings.billing_enabled is True


async def test_empty_mp_price_env_var_means_not_for_sale(monkeypatch):
    from app.config import Settings

    # docker-compose pasa ${VAR:-} como string vacio.
    monkeypatch.setenv("MP_PRICE_MODULE_STUDY", "")
    monkeypatch.setenv("MP_PRICE_MODULE_LIBRARY", "450000")
    s = Settings()
    assert s.MP_PRICE_MODULE_STUDY is None
    assert s.MP_PRICE_MODULE_LIBRARY == 450000
    assert s.BILLING_PROVIDER == "mercadopago"


async def test_unknown_billing_provider_is_rejected(monkeypatch):
    from pydantic import ValidationError

    from app.config import Settings

    monkeypatch.setenv("BILLING_PROVIDER", "paypal")
    with pytest.raises(ValidationError):
        Settings()


# ── Tienda ───────────────────────────────────────────────────────────────────

async def test_store_shows_mp_prices_and_coming_soon(
    api_auth_client, db_session, test_user, mp_enabled
):
    await ModulesService(db_session).grant(test_user.id, "library")

    data = (await api_auth_client.get("/api/v1/billing/store")).json()
    items = {i["key"]: i for i in data["items"]}

    assert data["billing_enabled"] is True
    assert items["study"]["amount"] == 299900
    assert items["study"]["currency"] == "ars"
    assert items["study"]["owned"] is False
    assert items["library"]["owned"] is True
    # Sin precio cargado: "Próximamente".
    assert items["vehicle"]["amount"] is None
    assert items["vehicle"]["currency"] is None
    # Los precios salen de la config: la tienda no llama a Mercado Pago.
    assert mp_enabled.requests == []


async def test_store_without_mp_token_has_no_prices(api_auth_client, monkeypatch):
    monkeypatch.setattr(settings, "MP_PRICE_MODULE_STUDY", 299900)
    data = (await api_auth_client.get("/api/v1/billing/store")).json()
    assert data["billing_enabled"] is False
    assert all(i["amount"] is None for i in data["items"])


# ── Checkout ─────────────────────────────────────────────────────────────────

async def test_checkout_returns_the_init_point(api_auth_client, test_user, mp_enabled):
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 200
    assert resp.json()["url"] == (
        "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=pref_123"
    )

    (req,) = mp_enabled.requests
    assert str(req.url) == "https://api.mercadopago.com/checkout/preferences"
    assert req.headers["Authorization"] == "Bearer APP_USR-test-token"

    pref = mp_enabled.preference_payload()
    (item,) = pref["items"]
    assert item["title"] == "Estudio & Universidad"
    assert item["quantity"] == 1
    assert item["unit_price"] == 2999.0  # en pesos, no en centavos
    assert item["currency_id"] == "ARS"
    assert pref["external_reference"] == f"{test_user.id}:study"
    assert pref["metadata"] == {"user_id": test_user.id, "module_key": "study"}
    assert pref["auto_return"] == "approved"
    assert pref["back_urls"] == {
        "success": "https://cancen.example.com/store?checkout=ok",
        "failure": "https://cancen.example.com/store?checkout=cancel",
        "pending": "https://cancen.example.com/store?checkout=pending",
    }
    notification = urlparse(pref["notification_url"])
    assert f"{notification.scheme}://{notification.netloc}{notification.path}" == (
        "https://cancen.example.com/api/v1/billing/webhook/mercadopago"
    )
    assert parse_qs(notification.query) == {"source_news": ["webhooks"]}


async def test_checkout_uses_the_configured_return_urls(api_auth_client, mp_enabled, monkeypatch):
    monkeypatch.setattr(settings, "BILLING_SUCCESS_URL", "https://cancen.example.com/listo")
    monkeypatch.setattr(settings, "BILLING_CANCEL_URL", "https://cancen.example.com/nada")
    await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})

    back_urls = mp_enabled.preference_payload()["back_urls"]
    assert back_urls["success"] == "https://cancen.example.com/listo"
    assert back_urls["failure"] == "https://cancen.example.com/nada"


async def test_checkout_with_app_redirect_returns_to_the_app(api_auth_client, mp_enabled):
    resp = await api_auth_client.post(
        "/api/v1/billing/checkout",
        params={"module": "study", "app_redirect": "cancen://store"},
    )
    assert resp.status_code == 200
    assert mp_enabled.preference_payload()["back_urls"] == {
        "success": "cancen://store?checkout=ok",
        "failure": "cancen://store?checkout=cancel",
        "pending": "cancen://store?checkout=pending",
    }


async def test_checkout_rejects_an_invalid_app_redirect(api_auth_client, mp_enabled):
    resp = await api_auth_client.post(
        "/api/v1/billing/checkout",
        params={"module": "study", "app_redirect": "https://evil.example.com/steal"},
    )
    assert resp.status_code == 400
    assert mp_enabled.requests == []


async def test_checkout_unavailable_without_mp_token(api_auth_client, monkeypatch):
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    monkeypatch.setattr(settings, "MP_PRICE_MODULE_STUDY", 299900)
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 503


async def test_checkout_blocked_for_unverified_email(client, db_session, mp_enabled):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    user = User(
        email="sinverificar@test.com",
        password_hash=hash_password("test123"),
        full_name="Sin Verificar",
        is_active=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await client.post("/auth/api/login", json={"email": "sinverificar@test.com", "password": "test123"})

    resp = await client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 403
    assert mp_enabled.requests == []


async def test_checkout_rejects_a_template_without_mp_price(api_auth_client, mp_enabled):
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "vehicle"})
    assert resp.status_code == 400


async def test_checkout_rejects_a_base_template(api_auth_client, mp_enabled):
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "habits"})
    assert resp.status_code == 400


async def test_checkout_rejects_something_already_owned(
    api_auth_client, db_session, test_user, mp_enabled
):
    await ModulesService(db_session).grant(test_user.id, "study")
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 400
    assert mp_enabled.requests == []


async def test_checkout_mp_api_error_is_a_502(api_auth_client, mp_enabled):
    mp_enabled.fail_with = 500
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 502


async def test_checkout_is_rate_limited_per_user(api_auth_client, test_user, mp_enabled):
    from app.core.http_security import billing_rate_limiter

    for _ in range(10):
        assert await billing_rate_limiter.hit(str(test_user.id)) == 0

    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 429


# ── Webhook ──────────────────────────────────────────────────────────────────

async def test_webhook_unavailable_when_secret_not_configured(client):
    resp = await client.post(WEBHOOK_URL, params={"data.id": "1", "type": "payment"}, content="{}")
    assert resp.status_code == 503


async def test_webhook_rejects_invalid_signature(client, mp_enabled):
    headers = _signed_headers("1234567890")
    headers["x-signature"] = "ts=1704908010,v1=deadbeef"
    resp = await _notify(client, "1234567890", headers=headers)
    assert resp.status_code == 400
    assert mp_enabled.requests == []


async def test_webhook_rejects_missing_signature(client, mp_enabled):
    resp = await _notify(client, "1234567890", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400


async def test_webhook_rejects_a_signature_for_another_payment(client, mp_enabled):
    # Una firma valida no se puede reusar cambiando el data.id.
    resp = await _notify(client, "999", headers=_signed_headers("1234567890"))
    assert resp.status_code == 400


async def test_webhook_rejects_a_signature_made_with_another_secret(client, mp_enabled):
    manifest = "id:1234567890;request-id:req-abc-123;ts:1704908010;"
    v1 = hmac.new(b"otro-secreto", manifest.encode(), hashlib.sha256).hexdigest()
    headers = {"x-signature": f"ts=1704908010,v1={v1}", "x-request-id": "req-abc-123"}
    resp = await _notify(client, "1234567890", headers=headers)
    assert resp.status_code == 400


async def test_webhook_grants_an_approved_payment(
    api_auth_client, db_session, test_user, mp_enabled
):
    mp_enabled.payments["1234567890"] = _payment(user_id=test_user.id)

    resp = await _notify(api_auth_client, "1234567890")
    assert resp.status_code == 200

    (req,) = mp_enabled.requests
    assert str(req.url) == "https://api.mercadopago.com/v1/payments/1234567890"
    assert req.headers["Authorization"] == "Bearer APP_USR-test-token"

    modules = (await api_auth_client.get("/api/v1/modules")).json()
    study = next(m for m in modules if m["key"] == "study")
    assert study["owned"] is True
    assert study["enabled"] is True

    compra = (await db_session.execute(select(ModulePurchase))).scalars().one()
    assert compra.amount_paid == 299900
    assert compra.currency == "ars"
    assert compra.stripe_session_id == "1234567890"


async def test_webhook_falls_back_to_metadata(api_auth_client, db_session, test_user, mp_enabled):
    payment = _payment(user_id=test_user.id)
    payment["external_reference"] = None
    mp_enabled.payments["1234567890"] = payment

    await _notify(api_auth_client, "1234567890")
    assert "study" in await ModulesService(db_session).owned_keys(test_user.id)


@pytest.mark.parametrize("status", ["pending", "in_process", "rejected", "cancelled", None])
async def test_webhook_does_not_grant_an_unapproved_payment(
    api_auth_client, db_session, test_user, mp_enabled, status
):
    payment = _payment(user_id=test_user.id, status=status)
    if status is None:
        del payment["status"]
    mp_enabled.payments["1234567890"] = payment

    resp = await _notify(api_auth_client, "1234567890")
    assert resp.status_code == 200
    assert await ModulesService(db_session).owned_keys(test_user.id) == set()


async def test_webhook_does_not_trust_the_notification_body(
    api_auth_client, db_session, test_user, mp_enabled
):
    # El cuerpo dice "approved" pero MP dice "pending": manda MP.
    mp_enabled.payments["1234567890"] = _payment(user_id=test_user.id, status="pending")
    body = json.dumps(
        {"type": "payment", "data": {"id": "1234567890"}, "status": "approved",
         "external_reference": f"{test_user.id}:study"}
    )
    resp = await api_auth_client.post(
        WEBHOOK_URL,
        params={"data.id": "1234567890", "type": "payment"},
        content=body,
        headers=_signed_headers("1234567890"),
    )
    assert resp.status_code == 200
    assert await ModulesService(db_session).owned_keys(test_user.id) == set()


async def test_webhook_is_idempotent(api_auth_client, db_session, test_user, mp_enabled):
    # MP reintenta las notificaciones: la segunda no puede duplicar la compra.
    mp_enabled.payments["1234567890"] = _payment(user_id=test_user.id)
    assert (await _notify(api_auth_client, "1234567890")).status_code == 200
    assert (await _notify(api_auth_client, "1234567890")).status_code == 200

    compras = (await db_session.execute(select(ModulePurchase))).scalars().all()
    assert len(list(compras)) == 1


async def test_webhook_for_an_unknown_template_is_ignored(
    api_auth_client, db_session, test_user, mp_enabled
):
    mp_enabled.payments["1234567890"] = _payment(user_id=test_user.id, module_key="inventada")
    resp = await _notify(api_auth_client, "1234567890")
    assert resp.status_code == 200
    assert await ModulesService(db_session).owned_keys(test_user.id) == set()


async def test_webhook_for_an_unknown_user_is_ignored_without_error(
    client, db_session, mp_enabled
):
    mp_enabled.payments["1234567890"] = _payment(user_id="00000000-0000-0000-0000-000000000000")
    resp = await _notify(client, "1234567890")
    assert resp.status_code == 200
    assert (await db_session.execute(select(ModulePurchase))).scalars().all() == []


async def test_webhook_without_purchase_reference_is_ignored(client, db_session, mp_enabled):
    mp_enabled.payments["1234567890"] = _payment(user_id=None)
    resp = await _notify(client, "1234567890")
    assert resp.status_code == 200
    assert (await db_session.execute(select(ModulePurchase))).scalars().all() == []


async def test_webhook_for_a_nonexistent_payment_is_acknowledged(client, mp_enabled):
    # El "simular notificación" del panel de MP manda un id que no existe.
    resp = await _notify(client, "123456")
    assert resp.status_code == 200


async def test_non_payment_topic_is_acknowledged(client, mp_enabled):
    resp = await _notify(client, "987654", type_="merchant_order")
    assert resp.status_code == 200
    # Ni siquiera se consulta a MP.
    assert mp_enabled.requests == []


async def test_webhook_mp_api_error_asks_for_a_retry(
    api_auth_client, db_session, test_user, mp_enabled
):
    # Si MP no responde, != 2xx para que reintente en vez de perder la compra.
    mp_enabled.fail_with = 503
    resp = await _notify(api_auth_client, "1234567890")
    assert resp.status_code == 502

    mp_enabled.fail_with = None
    mp_enabled.payments["1234567890"] = _payment(user_id=test_user.id)
    assert (await _notify(api_auth_client, "1234567890")).status_code == 200
    assert "study" in await ModulesService(db_session).owned_keys(test_user.id)


# ── Firma ────────────────────────────────────────────────────────────────────

async def test_signature_lowercases_alphanumeric_ids():
    manifest = "id:abc123;request-id:r1;ts:10;"
    v1 = hmac.new(b"s", manifest.encode(), hashlib.sha256).hexdigest()
    assert mercadopago.verify_signature(f"ts=10,v1={v1}", "r1", "ABC123", "s")


async def test_signature_omits_missing_parts_from_the_manifest():
    v1 = hmac.new(b"s", b"id:42;ts:10;", hashlib.sha256).hexdigest()
    assert mercadopago.verify_signature(f"ts=10, v1={v1}", "", "42", "s")


async def test_signature_header_without_ts_or_v1_is_invalid():
    assert not mercadopago.verify_signature("v1=abc", "r1", "42", "s")
    assert not mercadopago.verify_signature("ts=10", "r1", "42", "s")
    assert not mercadopago.verify_signature("", "r1", "42", "s")


@pytest.mark.asyncio
async def test_grant_duplicado_concurrente_no_revienta(db_session, test_user, monkeypatch):
    """Dos notificaciones del mismo pago pasan a la vez el SELECT de
    idempotencia; la segunda choca con el UNIQUE. Tiene que ser un no-op, no un
    500 (MP reintentaria en loop)."""
    from sqlalchemy.exc import IntegrityError

    from app.modules.modulos.service import ModulesService

    async def boom():
        raise IntegrityError("INSERT", {}, Exception("uq_module_purchase_user_key"))

    monkeypatch.setattr(db_session, "commit", boom)
    assert await ModulesService(db_session).grant(str(test_user.id), "study") is False
