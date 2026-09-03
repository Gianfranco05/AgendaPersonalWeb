import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.redirect_safety import validate_app_redirect
from app.database import get_db
from app.modules.auth.models import User
from app.modules.billing.service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscriptionOut(BaseModel):
    plan: str
    status: Optional[str] = None
    is_pro: bool
    current_period_end: Optional[datetime] = None
    billing_enabled: bool


class CheckoutSessionOut(BaseModel):
    url: str


class PriceOut(BaseModel):
    tier: str
    amount: int
    currency: str
    interval: Optional[str] = None


class PlansOut(BaseModel):
    billing_enabled: bool
    plans: list[PriceOut]


# Cada tier mapea a un Price ID de Stripe (configurable, algunos pueden estar
# vacios todavia) y a un modo de Checkout: "subscription" para recurrente,
# "payment" para pago unico (Elite/lifetime, no genera objeto de suscripcion).
_TIERS = {
    "pro_monthly": {"price_attr": "STRIPE_PRICE_ID_PRO", "mode": "subscription"},
    "pro_annual": {"price_attr": "STRIPE_PRICE_ID_PRO_ANNUAL", "mode": "subscription"},
    "elite": {"price_attr": "STRIPE_PRICE_ID_ELITE", "mode": "payment"},
}


def _require_billing_configured() -> None:
    if not settings.billing_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El pago no está configurado en este entorno",
        )


def _stripe():
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _checkout_return_urls(app_redirect: Optional[str]) -> tuple[str, str]:
    """success_url/cancel_url para la Checkout Session o el Billing Portal.

    Con `app_redirect` (mobile, deep link a la app) Stripe redirige el
    navegador ahi directamente al terminar — no hace falta un roundtrip de
    estado firmado como en el login con Google, porque el redirect final lo
    hace Stripe, no nosotros.
    """
    if app_redirect:
        validate_app_redirect(app_redirect)
        return f"{app_redirect}?checkout=ok", f"{app_redirect}?checkout=cancel"
    return (
        settings.BILLING_SUCCESS_URL
        or f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ajustes?checkout=ok",
        settings.BILLING_CANCEL_URL
        or f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ajustes?checkout=cancel",
    )


@router.get("/me", response_model=SubscriptionOut)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await BillingService(db).get_or_create(str(current_user.id))
    return SubscriptionOut(
        plan=sub.plan,
        status=sub.status,
        is_pro=sub.is_pro,
        current_period_end=sub.current_period_end,
        billing_enabled=settings.billing_enabled,
    )


@router.get("/plans", response_model=PlansOut)
async def get_plans():
    if not settings.billing_enabled:
        return PlansOut(billing_enabled=False, plans=[])

    stripe = _stripe()
    plans: list[PriceOut] = []
    for tier, cfg in _TIERS.items():
        price_id = getattr(settings, cfg["price_attr"])
        if not price_id:
            continue
        try:
            price = stripe.Price.retrieve(price_id)
        except Exception:
            logger.exception("Fallo obteniendo el precio de Stripe para %s", tier)
            continue
        plans.append(
            PriceOut(
                tier=tier,
                amount=price.unit_amount,
                currency=price.currency,
                interval=price.recurring["interval"] if price.recurring else None,
            )
        )

    return PlansOut(billing_enabled=True, plans=plans)


@router.post("/checkout", response_model=CheckoutSessionOut)
async def create_checkout_session(
    tier: str = "pro_monthly",
    app_redirect: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_billing_configured()
    if tier not in _TIERS:
        raise HTTPException(status_code=400, detail="Plan inválido")

    price_id = getattr(settings, _TIERS[tier]["price_attr"])
    if not price_id:
        raise HTTPException(status_code=400, detail="Este plan todavía no está disponible")

    success_url, cancel_url = _checkout_return_urls(app_redirect)

    stripe = _stripe()
    service = BillingService(db)
    sub = await service.get_or_create(str(current_user.id))

    if not sub.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.full_name,
            metadata={"user_id": str(current_user.id)},
        )
        sub = await service.link_customer(str(current_user.id), customer.id)

    try:
        session = stripe.checkout.Session.create(
            mode=_TIERS[tier]["mode"],
            customer=sub.stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(current_user.id), "tier": tier},
        )
    except Exception:
        logger.exception("Fallo creando la Checkout Session de Stripe")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")

    return CheckoutSessionOut(url=session.url)


@router.post("/portal", response_model=CheckoutSessionOut)
async def create_portal_session(
    app_redirect: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_billing_configured()
    stripe = _stripe()

    sub = await BillingService(db).get_or_create(str(current_user.id))
    if not sub.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todavía no tenés una suscripción",
        )

    if app_redirect:
        validate_app_redirect(app_redirect)
        return_url = app_redirect
    else:
        return_url = settings.BILLING_SUCCESS_URL or f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ajustes"

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url,
        )
    except Exception:
        logger.exception("Fallo creando la sesión del portal de Stripe")
        raise HTTPException(status_code=502, detail="No se pudo abrir el portal")

    return CheckoutSessionOut(url=session.url)


# Eventos que cambian el derecho a Pro. checkout.session.completed no alcanza
# para suscripciones: no trae el estado ni las renovaciones o bajas
# posteriores. Para Elite (pago unico) es al reves: no existe un objeto de
# suscripcion en absoluto, asi que checkout.session.completed es la unica
# fuente de verdad posible.
_SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook no configurado",
        )

    import stripe

    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        # Verificar la firma es lo unico que separa esto de un endpoint publico
        # donde cualquiera se regala el plan Pro.
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        logger.warning("Webhook de Stripe con firma inválida")
        raise HTTPException(status_code=400, detail="Firma inválida")
    except ValueError:
        logger.warning("Webhook de Stripe con payload ilegible")
        raise HTTPException(status_code=400, detail="Payload inválido")

    event_type = event["type"]

    if event_type in _SUBSCRIPTION_EVENTS:
        # construct_event devuelve StripeObject, que no expone .get(); se
        # reparsea el payload ya verificado para trabajar con dicts planos.
        data = json.loads(payload)["data"]["object"]
        await BillingService(db).apply_subscription_event(data)
    elif event_type == "checkout.session.completed":
        data = json.loads(payload)["data"]["object"]
        if data.get("mode") == "payment" and data.get("metadata", {}).get("tier") == "elite":
            customer_id = data.get("customer")
            if customer_id:
                await BillingService(db).apply_elite_purchase(customer_id)

    # 200 siempre que la firma sea valida: un evento que no manejamos no es un
    # error, y devolver != 2xx hace que Stripe lo reintente en loop.
    return {"received": True}
