import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.config import settings
from app.modules.billing.service import BillingService
from app.modules.modulos.models import ModulePurchase
from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio

WEBHOOK_SECRET = "whsec_test_secret"


@pytest_asyncio.fixture
async def billing_enabled(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_MODULE_STUDY", "price_study")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    return True


def _signed(payload: dict) -> tuple[str, dict]:
    """Firma un payload como lo haria Stripe, para no mockear construct_event."""
    body = json.dumps(payload)
    timestamp = int(time.time())
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return body, {
        "Stripe-Signature": f"t={timestamp},v1={signature}",
        "Content-Type": "application/json",
    }


def _checkout_event(
    module_key: str = "study",
    user_id: str | None = None,
    customer: str | None = None,
    payment_status: str = "paid",
    amount_total: int = 1500,
) -> dict:
    metadata: dict = {"module_key": module_key}
    if user_id:
        metadata["user_id"] = user_id
    return {
        "id": "evt_test",
        # Stripe manda "object": "event" en todos los webhooks y el SDK lo lee
        # para distinguir los eventos v2; sin esto construct_event falla.
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "mode": "payment",
                "customer": customer,
                "payment_status": payment_status,
                "amount_total": amount_total,
                "currency": "usd",
                "metadata": metadata,
            }
        },
    }


# ── Tienda ───────────────────────────────────────────────────────────────────

async def test_store_requires_auth(client):
    assert (await client.get("/api/v1/billing/store")).status_code == 401


async def test_store_lists_paid_templates_without_stripe(api_auth_client):
    """Sin Stripe configurado la tienda igual muestra el catalogo, sin precios."""
    resp = await api_auth_client.get("/api/v1/billing/store")
    assert resp.status_code == 200
    data = resp.json()

    assert data["billing_enabled"] is False
    keys = {i["key"] for i in data["items"]}
    assert keys == {"study", "library", "media", "work", "travel", "vehicle", "projects"}
    # Ninguna base se cuela en la tienda: vienen incluidas.
    assert "habits" not in keys
    assert all(i["amount"] is None for i in data["items"])
    assert all(i["owned"] is False for i in data["items"])


async def test_store_shows_prices_and_ownership(
    api_auth_client, db_session, test_user, billing_enabled, monkeypatch
):
    await ModulesService(db_session).grant(test_user.id, "study")

    fake_stripe = MagicMock()
    fake_stripe.Price.retrieve.return_value = MagicMock(unit_amount=1500, currency="usd")
    monkeypatch.setattr("app.modules.billing.api_routes._stripe", lambda: fake_stripe)

    data = (await api_auth_client.get("/api/v1/billing/store")).json()
    items = {i["key"]: i for i in data["items"]}

    assert data["billing_enabled"] is True
    assert items["study"]["owned"] is True
    assert items["study"]["amount"] == 1500
    assert items["study"]["currency"] == "usd"
    # Las que no tienen Price ID cargado siguen en el catalogo, sin precio.
    assert items["vehicle"]["amount"] is None


# ── Checkout ─────────────────────────────────────────────────────────────────

async def test_checkout_unavailable_without_stripe(api_auth_client):
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 503


async def test_checkout_rejects_a_base_template(api_auth_client, billing_enabled):
    # Las incluidas no se venden.
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "habits"})
    assert resp.status_code == 400


async def test_checkout_rejects_an_unknown_template(api_auth_client, billing_enabled):
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "bogus"})
    assert resp.status_code == 400


async def test_checkout_rejects_a_template_without_price(api_auth_client, billing_enabled):
    # billing_enabled solo carga el precio de study.
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "vehicle"})
    assert resp.status_code == 400


async def test_checkout_rejects_something_already_owned(
    api_auth_client, db_session, test_user, billing_enabled
):
    await ModulesService(db_session).grant(test_user.id, "study")
    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 400


async def test_checkout_is_rate_limited_per_user(api_auth_client, test_user, billing_enabled):
    from app.core.http_security import billing_rate_limiter

    # Bucket propio de billing (10/5min), keyed por user_id: agotarlo sin
    # gastar 10 requests HTTP reales, que ademas fallarian por "ya tenés esta
    # plantilla" al repetir.
    for _ in range(10):
        assert await billing_rate_limiter.hit(str(test_user.id)) == 0

    resp = await api_auth_client.post("/api/v1/billing/checkout", params={"module": "study"})
    assert resp.status_code == 429


async def test_checkout_rejects_an_invalid_app_redirect(api_auth_client, billing_enabled):
    resp = await api_auth_client.post(
        "/api/v1/billing/checkout",
        params={"module": "study", "app_redirect": "https://evil.example.com/steal"},
    )
    assert resp.status_code == 400


# ── Webhook ──────────────────────────────────────────────────────────────────

async def test_webhook_rejects_invalid_signature(client, billing_enabled):
    body, _ = _signed(_checkout_event())
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=body,
        headers={"Stripe-Signature": "t=1,v1=deadbeef", "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


async def test_webhook_rejects_missing_signature(client, billing_enabled):
    body, _ = _signed(_checkout_event())
    resp = await client.post(
        "/api/v1/billing/webhook", content=body, headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400


async def test_webhook_unavailable_when_secret_not_configured(client):
    resp = await client.post("/api/v1/billing/webhook", content="{}")
    assert resp.status_code == 503


async def test_webhook_grants_the_purchased_template(
    api_auth_client, db_session, test_user, billing_enabled
):
    body, headers = _signed(_checkout_event(user_id=test_user.id))
    resp = await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200

    modules = (await api_auth_client.get("/api/v1/modules")).json()
    study = next(m for m in modules if m["key"] == "study")
    assert study["owned"] is True
    assert study["enabled"] is True  # comprarla y no verla no tendria sentido

    compra = (await db_session.execute(select(ModulePurchase))).scalars().one()
    assert compra.amount_paid == 1500
    assert compra.currency == "usd"


async def test_webhook_identifies_the_user_by_stripe_customer(
    api_auth_client, db_session, test_user, billing_enabled
):
    """Si Stripe no devuelve el user_id en metadata, se resuelve por customer."""
    await BillingService(db_session).link_customer(test_user.id, "cus_real")

    body, headers = _signed(_checkout_event(user_id=None, customer="cus_real"))
    await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)

    assert "study" in await ModulesService(db_session).owned_keys(test_user.id)


async def test_webhook_is_idempotent(api_auth_client, db_session, test_user, billing_enabled):
    # Stripe reintenta los webhooks: la segunda entrega no puede duplicar la compra.
    body, headers = _signed(_checkout_event(user_id=test_user.id))
    await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)
    await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)

    compras = (await db_session.execute(select(ModulePurchase))).scalars().all()
    assert len(list(compras)) == 1


async def test_webhook_ignores_a_checkout_without_confirmed_payment(
    api_auth_client, db_session, test_user, billing_enabled
):
    body, headers = _signed(_checkout_event(user_id=test_user.id, payment_status="unpaid"))
    resp = await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200

    assert await ModulesService(db_session).owned_keys(test_user.id) == set()


async def test_webhook_without_payment_status_is_not_granted(
    api_auth_client, db_session, test_user, billing_enabled
):
    # Un Checkout Session real de Stripe siempre trae payment_status; si un
    # payload llega sin ese campo (payload inesperado/malformado) el fix debe
    # tratarlo como NO pagado, no como "paid" implicito.
    event = _checkout_event(user_id=test_user.id)
    del event["data"]["object"]["payment_status"]
    body = json.dumps(event)
    timestamp = int(time.time())
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    headers = {"Stripe-Signature": f"t={timestamp},v1={signature}", "Content-Type": "application/json"}

    resp = await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200
    assert await ModulesService(db_session).owned_keys(test_user.id) == set()


async def test_webhook_for_an_unknown_user_is_ignored_without_error(client, billing_enabled):
    body, headers = _signed(_checkout_event(user_id=None, customer="cus_desconocido"))
    resp = await client.post("/api/v1/billing/webhook", content=body, headers=headers)
    # 200 igual: si devolviera error, Stripe reintentaria este evento para siempre.
    assert resp.status_code == 200


async def test_webhook_for_an_unknown_template_is_ignored(
    api_auth_client, db_session, test_user, billing_enabled
):
    body, headers = _signed(_checkout_event(module_key="inventada", user_id=test_user.id))
    resp = await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200
    assert await ModulesService(db_session).owned_keys(test_user.id) == set()


async def test_unhandled_event_type_is_acknowledged(client, billing_enabled):
    body, headers = _signed(
        {"id": "evt_x", "object": "event", "type": "invoice.paid", "data": {"object": {}}}
    )
    resp = await client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200


# ── Gate de acceso por plantilla ─────────────────────────────────────────────

async def test_paid_template_endpoints_are_blocked_without_the_purchase(
    api_auth_client, billing_enabled
):
    resp = await api_auth_client.get("/api/v1/study/subjects")
    assert resp.status_code == 402


async def test_paid_template_endpoints_open_after_buying(
    api_auth_client, db_session, test_user, billing_enabled
):
    await ModulesService(db_session).grant(test_user.id, "study")
    assert (await api_auth_client.get("/api/v1/study/subjects")).status_code == 200


async def test_everything_is_open_when_billing_is_disabled(api_auth_client):
    # Self-hosted o dev sin Stripe: no se le puede cobrar a nadie, asi que
    # bloquear plantillas dejaria la app a medias.
    assert (await api_auth_client.get("/api/v1/study/subjects")).status_code == 200
