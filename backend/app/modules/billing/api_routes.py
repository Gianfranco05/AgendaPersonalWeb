import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.http_security import rate_limit_billing
from app.core.redirect_safety import validate_app_redirect
from app.database import get_db
from app.modules.auth.models import User
from app.modules.billing.service import BillingService
from app.modules.modulos.registry import MODULE_BY_KEY, PAID_MODULES
from app.modules.modulos.service import ModulesService, price_id_for

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class StoreItemOut(BaseModel):
    key: str
    label: str
    description: str
    icon: str
    owned: bool
    #: None cuando la plantilla todavia no tiene precio cargado en Stripe.
    amount: Optional[int] = None
    currency: Optional[str] = None


class StoreOut(BaseModel):
    billing_enabled: bool
    items: list[StoreItemOut]


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


async def _fetch_price(price_id: str) -> Optional[dict]:
    """Precio de Stripe, o None si no se pudo traer.

    Un precio mal configurado no puede tumbar la tienda entera: esa plantilla
    aparece sin precio y las demas se siguen viendo.
    """
    stripe = _stripe()
    try:
        price = await asyncio.to_thread(stripe.Price.retrieve, price_id)
        return {"amount": price.unit_amount, "currency": price.currency}
    except Exception:
        logger.exception("Fallo obteniendo el precio de Stripe %s", price_id)
        return None


@router.get("/store", response_model=StoreOut)
async def get_store(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owned = await ModulesService(db).owned_keys(str(current_user.id))

    price_ids = {m.key: price_id_for(m) for m in PAID_MODULES}
    con_precio = {k: v for k, v in price_ids.items() if v}
    # En paralelo: son varias llamadas a Stripe y en serie se notan al abrir la
    # tienda.
    resultados = await asyncio.gather(
        *(_fetch_price(pid) for pid in con_precio.values())
    ) if con_precio and settings.billing_enabled else []
    precios = dict(zip(con_precio.keys(), resultados))

    items = []
    for m in PAID_MODULES:
        precio = precios.get(m.key)
        items.append(
            StoreItemOut(
                key=m.key,
                label=m.label,
                description=m.description,
                icon=m.icon,
                owned=m.key in owned,
                amount=precio["amount"] if precio else None,
                currency=precio["currency"] if precio else None,
            )
        )

    return StoreOut(billing_enabled=settings.billing_enabled, items=items)


@router.post(
    "/checkout", response_model=CheckoutSessionOut, dependencies=[Depends(rate_limit_billing)]
)
async def create_checkout_session(
    module: str,
    app_redirect: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_billing_configured()

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenés que verificar tu email antes de comprar una plantilla",
        )

    module_def = MODULE_BY_KEY.get(module)
    if module_def is None or module_def.is_base:
        raise HTTPException(status_code=400, detail="Plantilla inválida")

    price_id = price_id_for(module_def)
    if not price_id:
        raise HTTPException(status_code=400, detail="Esta plantilla todavía no está a la venta")

    modules = ModulesService(db)
    if module in await modules.owned_keys(str(current_user.id)):
        raise HTTPException(status_code=400, detail="Ya tenés esta plantilla")

    if app_redirect:
        validate_app_redirect(app_redirect)
        success_url = f"{app_redirect}?checkout=ok"
        cancel_url = f"{app_redirect}?checkout=cancel"
    else:
        base = settings.PUBLIC_BASE_URL.rstrip("/")
        success_url = settings.BILLING_SUCCESS_URL or f"{base}/ajustes?checkout=ok"
        cancel_url = settings.BILLING_CANCEL_URL or f"{base}/ajustes?checkout=cancel"

    stripe = _stripe()
    billing = BillingService(db)
    customer_id = await billing.get_customer_id(str(current_user.id))
    if not customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=current_user.full_name,
            metadata={"user_id": str(current_user.id)},
        )
        customer_id = await billing.link_customer(str(current_user.id), customer.id)

    try:
        session = stripe.checkout.Session.create(
            # Pago unico: la plantilla queda en la cuenta, no se renueva.
            mode="payment",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(current_user.id), "module_key": module},
        )
    except Exception:
        logger.exception("Fallo creando la Checkout Session de Stripe")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")

    return CheckoutSessionOut(url=session.url)


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
        # donde cualquiera se regala las plantillas.
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        logger.warning("Webhook de Stripe con firma inválida")
        raise HTTPException(status_code=400, detail="Firma inválida")
    except ValueError:
        logger.warning("Webhook de Stripe con payload ilegible")
        raise HTTPException(status_code=400, detail="Payload inválido")

    if event["type"] == "checkout.session.completed":
        # construct_event devuelve StripeObject, que no expone .get(); se
        # reparsea el payload ya verificado para trabajar con dicts planos.
        data = json.loads(payload)["data"]["object"]
        await _grant_purchase(db, data)

    # 200 siempre que la firma sea valida: un evento que no manejamos no es un
    # error, y devolver != 2xx hace que Stripe lo reintente en loop.
    return {"received": True}


async def _grant_purchase(db: AsyncSession, session: dict) -> None:
    metadata = session.get("metadata") or {}
    module_key = metadata.get("module_key")
    if not module_key:
        return

    # Solo se entrega con el pago cobrado: un checkout completado con pago
    # pendiente (algunos medios lo permiten) todavia no es una compra. Un
    # Checkout Session real de Stripe siempre trae payment_status, asi que un
    # valor ausente/no reconocido se trata como NO pagado (fail-closed) en vez
    # de dejarlo pasar — lo contrario habria otorgado el modulo gratis ante
    # cualquier payload inesperado.
    if session.get("payment_status") not in ("paid", "no_payment_required"):
        logger.info(
            "Checkout de %s sin pago confirmado (%s)", module_key, session.get("payment_status")
        )
        return

    user_id = metadata.get("user_id")
    if not user_id and session.get("customer"):
        user_id = await BillingService(db).user_id_for_customer(session["customer"])
    if not user_id:
        logger.warning("Checkout completado sin usuario identificable: %s", session.get("id"))
        return

    await ModulesService(db).grant(
        user_id=user_id,
        module_key=module_key,
        amount_paid=session.get("amount_total"),
        currency=session.get("currency"),
        stripe_session_id=session.get("id"),
    )
