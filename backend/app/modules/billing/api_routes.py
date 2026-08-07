import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.billing.models import Plan
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


@router.post("/checkout", response_model=CheckoutSessionOut)
async def create_checkout_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_billing_configured()
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
            mode="subscription",
            customer=sub.stripe_customer_id,
            line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
            success_url=settings.BILLING_SUCCESS_URL
            or f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ajustes?checkout=ok",
            cancel_url=settings.BILLING_CANCEL_URL
            or f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ajustes?checkout=cancel",
            metadata={"user_id": str(current_user.id)},
        )
    except Exception:
        logger.exception("Fallo creando la Checkout Session de Stripe")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")

    return CheckoutSessionOut(url=session.url)


@router.post("/portal", response_model=CheckoutSessionOut)
async def create_portal_session(
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

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=settings.BILLING_SUCCESS_URL
            or f"{settings.PUBLIC_BASE_URL.rstrip('/')}/ajustes",
        )
    except Exception:
        logger.exception("Fallo creando la sesión del portal de Stripe")
        raise HTTPException(status_code=502, detail="No se pudo abrir el portal")

    return CheckoutSessionOut(url=session.url)


# Eventos que cambian el derecho a Pro. checkout.session.completed no alcanza:
# no trae el estado de la suscripcion ni las renovaciones o bajas posteriores.
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

    if event["type"] in _SUBSCRIPTION_EVENTS:
        # construct_event devuelve StripeObject, que no expone .get(); se
        # reparsea el payload ya verificado para trabajar con dicts planos.
        data = json.loads(payload)["data"]["object"]
        await BillingService(db).apply_subscription_event(data)

    # 200 siempre que la firma sea valida: un evento que no manejamos no es un
    # error, y devolver != 2xx hace que Stripe lo reintente en loop.
    return {"received": True}
