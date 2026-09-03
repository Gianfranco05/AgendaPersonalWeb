import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.config import settings
from app.modules.billing.models import Plan, Subscription, SubscriptionStatus
from app.modules.billing.service import BillingService

pytestmark = pytest.mark.asyncio

WEBHOOK_SECRET = "whsec_test_secret"


@pytest_asyncio.fixture
async def billing_enabled(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_PRICE_ID_PRO", "price_fake")
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


def _checkout_completed_event(customer_id: str, tier: str, mode: str = "payment") -> dict:
    return {
        "id": "evt_checkout",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": customer_id,
                "mode": mode,
                "metadata": {"tier": tier},
            }
        },
    }


def _subscription_event(customer_id: str, status: str, period_end_days: int = 30) -> dict:
    return {
        "id": "evt_test",
        # Stripe manda "object": "event" en todos los webhooks y el SDK lo lee
        # para distinguir los eventos v2; sin esto construct_event falla.
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": customer_id,
                "status": status,
                "current_period_end": int(
                    (datetime.now(timezone.utc) + timedelta(days=period_end_days)).timestamp()
                ),
            }
        },
    }


# ── Estado del plan ──────────────────────────────────────────────────────────

async def test_new_user_is_free(api_auth_client):
    resp = await api_auth_client.get("/api/v1/billing/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == Plan.FREE
    assert data["is_pro"] is False


async def test_billing_me_reports_whether_stripe_is_configured(api_auth_client):
    resp = await api_auth_client.get("/api/v1/billing/me")
    assert resp.json()["billing_enabled"] is False


async def test_checkout_unavailable_when_stripe_not_configured(api_auth_client):
    resp = await api_auth_client.post("/api/v1/billing/checkout")
    assert resp.status_code == 503


async def test_billing_endpoints_require_auth(client):
    assert (await client.get("/api/v1/billing/me")).status_code == 401
    assert (await client.post("/api/v1/billing/checkout")).status_code == 401


# ── Webhook ──────────────────────────────────────────────────────────────────

async def test_webhook_rejects_invalid_signature(client, billing_enabled):
    body, _ = _signed(_subscription_event("cus_x", SubscriptionStatus.ACTIVE))
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=body,
        headers={"Stripe-Signature": "t=1,v1=deadbeef", "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


async def test_webhook_rejects_missing_signature(client, billing_enabled):
    body, _ = _signed(_subscription_event("cus_x", SubscriptionStatus.ACTIVE))
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


async def test_webhook_unavailable_when_secret_not_configured(client):
    resp = await client.post("/api/v1/billing/webhook", content="{}")
    assert resp.status_code == 503


async def test_webhook_upgrades_user_to_pro(api_auth_client, db_session, test_user, billing_enabled):
    sub = await BillingService(db_session).get_or_create(test_user.id)
    sub.stripe_customer_id = "cus_real"
    await db_session.commit()

    body, headers = _signed(
        _subscription_event("cus_real", SubscriptionStatus.ACTIVE)
    )
    resp = await api_auth_client.post(
        "/api/v1/billing/webhook", content=body, headers=headers
    )
    assert resp.status_code == 200

    me = await api_auth_client.get("/api/v1/billing/me")
    assert me.json()["plan"] == Plan.PRO
    assert me.json()["is_pro"] is True


async def test_webhook_cancellation_returns_user_to_free(
    api_auth_client, db_session, test_user, billing_enabled
):
    sub = await BillingService(db_session).get_or_create(test_user.id)
    sub.stripe_customer_id = "cus_real"
    sub.plan = Plan.PRO
    sub.status = SubscriptionStatus.ACTIVE
    await db_session.commit()

    body, headers = _signed(
        _subscription_event("cus_real", SubscriptionStatus.CANCELED)
    )
    await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)

    me = await api_auth_client.get("/api/v1/billing/me")
    assert me.json()["plan"] == Plan.FREE
    assert me.json()["is_pro"] is False


async def test_webhook_for_unknown_customer_is_ignored_without_error(
    client, db_session, billing_enabled
):
    body, headers = _signed(
        _subscription_event("cus_desconocido", SubscriptionStatus.ACTIVE)
    )
    resp = await client.post("/api/v1/billing/webhook", content=body, headers=headers)
    # 200 igual: si devolviera error, Stripe reintentaria este evento para siempre.
    assert resp.status_code == 200

    result = await db_session.execute(
        select(Subscription).where(Subscription.stripe_customer_id == "cus_desconocido")
    )
    assert result.scalar_one_or_none() is None


async def test_unhandled_event_type_is_acknowledged(client, billing_enabled):
    body, headers = _signed({
        "id": "evt_x",
        "object": "event",
        "type": "invoice.paid",
        "data": {"object": {}},
    })
    resp = await client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200


# ── Derecho al plan (Subscription.is_pro) ────────────────────────────────────

def _sub(**kwargs) -> Subscription:
    defaults = {
        "user_id": "u1",
        "plan": Plan.PRO,
        "status": SubscriptionStatus.ACTIVE,
        "current_period_end": datetime.now(timezone.utc) + timedelta(days=10),
    }
    return Subscription(**{**defaults, **kwargs})


async def test_past_due_still_has_access():
    # Stripe reintenta el cobro varios dias: cortar al primer fallo de tarjeta
    # echaria a clientes que solo tienen que actualizar el medio de pago.
    assert _sub(status=SubscriptionStatus.PAST_DUE).is_pro is True


async def test_trialing_has_access():
    assert _sub(status=SubscriptionStatus.TRIALING).is_pro is True


async def test_expired_period_loses_access():
    expired = _sub(current_period_end=datetime.now(timezone.utc) - timedelta(days=1))
    assert expired.is_pro is False


async def test_canceled_status_loses_access():
    assert _sub(status=SubscriptionStatus.CANCELED).is_pro is False


async def test_free_plan_is_never_pro():
    assert _sub(plan=Plan.FREE, status=SubscriptionStatus.ACTIVE).is_pro is False


# ── Gate require_pro ─────────────────────────────────────────────────────────

async def test_require_pro_blocks_free_user(db_session, test_user, billing_enabled):
    from fastapi import HTTPException
    from app.core.plans import current_user_is_pro, require_pro

    is_pro = await current_user_is_pro(current_user=test_user, db=db_session)
    assert is_pro is False

    with pytest.raises(HTTPException) as exc:
        await require_pro(is_pro=is_pro)
    assert exc.value.status_code == 402


async def test_require_pro_allows_pro_user(db_session, test_user, billing_enabled):
    from app.core.plans import current_user_is_pro, require_pro

    sub = await BillingService(db_session).get_or_create(test_user.id)
    sub.plan = Plan.PRO
    sub.status = SubscriptionStatus.ACTIVE
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=10)
    await db_session.commit()

    is_pro = await current_user_is_pro(current_user=test_user, db=db_session)
    assert is_pro is True
    assert await require_pro(is_pro=is_pro) is None


async def test_everything_is_pro_when_billing_is_disabled(db_session, test_user):
    # Self-hosted o dev sin Stripe: no se le puede cobrar a nadie, asi que no
    # tiene sentido bloquear features.
    from app.core.plans import current_user_is_pro

    assert await current_user_is_pro(current_user=test_user, db=db_session) is True


async def test_elite_plan_is_always_pro_and_never_expires():
    # Pago unico: no tiene current_period_end (nada que vencer) ni depende de status.
    assert _sub(plan=Plan.ELITE, status=None, current_period_end=None).is_pro is True


# ── Tiers / precios / app_redirect (mobile) ──────────────────────────────────

async def test_plans_empty_when_billing_disabled(api_auth_client):
    resp = await api_auth_client.get("/api/v1/billing/plans")
    assert resp.status_code == 200
    assert resp.json() == {"billing_enabled": False, "plans": []}


async def test_plans_lists_only_configured_tiers(api_auth_client, billing_enabled, monkeypatch):
    from unittest.mock import MagicMock

    fake_price = MagicMock(unit_amount=799, currency="usd", recurring={"interval": "month"})
    fake_stripe = MagicMock()
    fake_stripe.Price.retrieve.return_value = fake_price
    monkeypatch.setattr(
        "app.modules.billing.api_routes._stripe", lambda: fake_stripe
    )

    resp = await api_auth_client.get("/api/v1/billing/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert data["billing_enabled"] is True
    # billing_enabled solo configura STRIPE_PRICE_ID_PRO: anual y elite quedan afuera.
    assert len(data["plans"]) == 1
    assert data["plans"][0] == {
        "tier": "pro_monthly",
        "amount": 799,
        "currency": "usd",
        "interval": "month",
    }


async def test_checkout_rejects_invalid_tier(api_auth_client, billing_enabled):
    resp = await api_auth_client.post("/api/v1/billing/checkout?tier=bogus")
    assert resp.status_code == 400


async def test_checkout_rejects_unconfigured_tier(api_auth_client, billing_enabled):
    # billing_enabled solo configura STRIPE_PRICE_ID_PRO, no elite ni anual.
    resp = await api_auth_client.post("/api/v1/billing/checkout?tier=elite")
    assert resp.status_code == 400


async def test_checkout_rejects_invalid_app_redirect(api_auth_client, billing_enabled):
    resp = await api_auth_client.post(
        "/api/v1/billing/checkout",
        params={"app_redirect": "https://evil.example.com/steal"},
    )
    assert resp.status_code == 400


async def test_portal_rejects_invalid_app_redirect(
    api_auth_client, db_session, test_user, billing_enabled
):
    sub = await BillingService(db_session).get_or_create(test_user.id)
    sub.stripe_customer_id = "cus_real"
    await db_session.commit()

    resp = await api_auth_client.post(
        "/api/v1/billing/portal",
        params={"app_redirect": "https://evil.example.com"},
    )
    assert resp.status_code == 400


# ── Webhook: checkout.session.completed (Elite / pago unico) ────────────────

async def test_webhook_elite_purchase_upgrades_user(
    api_auth_client, db_session, test_user, billing_enabled
):
    sub = await BillingService(db_session).get_or_create(test_user.id)
    sub.stripe_customer_id = "cus_real"
    await db_session.commit()

    body, headers = _signed(_checkout_completed_event("cus_real", "elite"))
    resp = await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 200

    me = await api_auth_client.get("/api/v1/billing/me")
    data = me.json()
    assert data["plan"] == Plan.ELITE
    assert data["is_pro"] is True
    assert data["current_period_end"] is None


async def test_webhook_checkout_completed_ignores_subscription_mode(
    api_auth_client, db_session, test_user, billing_enabled
):
    # El checkout.session.completed de una suscripcion (mode="subscription") no
    # debe tocar nada: el estado real de esas lo dan customer.subscription.*.
    sub = await BillingService(db_session).get_or_create(test_user.id)
    sub.stripe_customer_id = "cus_real"
    await db_session.commit()

    body, headers = _signed(
        _checkout_completed_event("cus_real", "pro_monthly", mode="subscription")
    )
    await api_auth_client.post("/api/v1/billing/webhook", content=body, headers=headers)

    me = await api_auth_client.get("/api/v1/billing/me")
    assert me.json()["plan"] == Plan.FREE
