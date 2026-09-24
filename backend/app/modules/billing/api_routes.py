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
from app.modules.billing import mercadopago
from app.modules.billing.service import BillingService
from app.modules.modulos.registry import MODULE_BY_KEY, PAID_MODULES, ModuleDef
from app.modules.modulos.service import ModulesService, is_for_sale, mp_price_for, price_id_for

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class StoreItemOut(BaseModel):
    key: str
    label: str
    description: str
    icon: str
    owned: bool
    #: None cuando la plantilla todavia no tiene precio cargado.
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


async def _stripe_prices() -> dict[str, Optional[dict]]:
    price_ids = {m.key: price_id_for(m) for m in PAID_MODULES}
    con_precio = {k: v for k, v in price_ids.items() if v}
    # En paralelo: son varias llamadas a Stripe y en serie se notan al abrir la
    # tienda.
    resultados = await asyncio.gather(
        *(_fetch_price(pid) for pid in con_precio.values())
    ) if con_precio else []
    return dict(zip(con_precio.keys(), resultados))


def _mercadopago_prices() -> dict[str, dict]:
    # MP no tiene catalogo de precios: el monto sale de la config y viaja en
    # cada preferencia, asi que no hay llamada externa.
    currency = settings.BILLING_CURRENCY.lower()
    precios = {}
    for m in PAID_MODULES:
        amount = mp_price_for(m)
        if amount is not None:
            precios[m.key] = {"amount": amount, "currency": currency}
    return precios


@router.get("/store", response_model=StoreOut)
async def get_store(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owned = await ModulesService(db).owned_keys(str(current_user.id))

    if not settings.billing_enabled:
        precios: dict = {}
    elif settings.BILLING_PROVIDER == "stripe":
        precios = await _stripe_prices()
    else:
        precios = _mercadopago_prices()

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

    if not is_for_sale(module_def):
        raise HTTPException(status_code=400, detail="Esta plantilla todavía no está a la venta")

    modules = ModulesService(db)
    if module in await modules.owned_keys(str(current_user.id)):
        raise HTTPException(status_code=400, detail="Ya tenés esta plantilla")

    if app_redirect:
        validate_app_redirect(app_redirect)
        success_url = f"{app_redirect}?checkout=ok"
        cancel_url = f"{app_redirect}?checkout=cancel"
        pending_url = f"{app_redirect}?checkout=pending"
    else:
        # /store es la pagina de la SPA que lee ?checkout= (banner y
        # revalidacion); la SPA no tiene /ajustes y lo redirigia a "/",
        # perdiendo el aviso de compra confirmada.
        base = settings.PUBLIC_BASE_URL.rstrip("/")
        success_url = settings.BILLING_SUCCESS_URL or f"{base}/store?checkout=ok"
        cancel_url = settings.BILLING_CANCEL_URL or f"{base}/store?checkout=cancel"
        pending_url = f"{base}/store?checkout=pending"

    if settings.BILLING_PROVIDER == "stripe":
        url = await _stripe_checkout(db, current_user, module_def, success_url, cancel_url)
    else:
        url = await _mercadopago_checkout(
            current_user, module_def, success_url, cancel_url, pending_url
        )
    return CheckoutSessionOut(url=url)


async def _stripe_checkout(
    db: AsyncSession, current_user: User, module_def: ModuleDef, success_url: str, cancel_url: str
) -> str:
    stripe = _stripe()
    billing = BillingService(db)
    customer_id = await billing.get_customer_id(str(current_user.id))
    if not customer_id:
        try:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": str(current_user.id)},
            )
        except Exception:
            logger.exception("Fallo creando el Customer de Stripe")
            raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")
        customer_id = await billing.link_customer(str(current_user.id), customer.id)

    try:
        session = stripe.checkout.Session.create(
            # Pago unico: la plantilla queda en la cuenta, no se renueva.
            mode="payment",
            customer=customer_id,
            line_items=[{"price": price_id_for(module_def), "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(current_user.id), "module_key": module_def.key},
        )
    except Exception:
        logger.exception("Fallo creando la Checkout Session de Stripe")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")

    return session.url


async def _mercadopago_checkout(
    current_user: User,
    module_def: ModuleDef,
    success_url: str,
    failure_url: str,
    pending_url: str,
) -> str:
    user_id = str(current_user.id)
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    preference = {
        "items": [
            {
                "id": module_def.key,
                "title": module_def.label,
                "quantity": 1,
                # MP recibe el precio en unidades (pesos), no en centavos.
                "unit_price": mp_price_for(module_def) / 100,
                "currency_id": settings.BILLING_CURRENCY.upper(),
            }
        ],
        # external_reference es lo que el webhook usa para saber a quien darle
        # que; metadata es respaldo por si alguna vez viene vacio.
        "external_reference": f"{user_id}:{module_def.key}",
        "metadata": {"user_id": user_id, "module_key": module_def.key},
        "back_urls": {"success": success_url, "failure": failure_url, "pending": pending_url},
        "auto_return": "approved",
        # source_news=webhooks: sin esto MP manda ademas las notificaciones
        # IPN viejas (?topic=&id=), que no traen la firma x-signature.
        "notification_url": f"{base}/api/v1/billing/webhook/mercadopago?source_news=webhooks",
    }
    try:
        created = await mercadopago.create_preference(preference)
        return created["init_point"]
    except Exception:
        logger.exception("Fallo creando la preferencia de Mercado Pago")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")


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


@router.post("/webhook/mercadopago", include_in_schema=False)
async def mercadopago_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not settings.MERCADOPAGO_WEBHOOK_SECRET or not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook no configurado",
        )

    # Solo se confia en data.id del query string: es lo que cubre la firma.
    data_id = request.query_params.get("data.id", "")
    # Igual que con Stripe, la firma es lo unico que separa esto de un
    # endpoint publico donde cualquiera se regala las plantillas.
    if not mercadopago.verify_signature(
        request.headers.get("x-signature", ""),
        request.headers.get("x-request-id", ""),
        data_id,
        settings.MERCADOPAGO_WEBHOOK_SECRET,
    ):
        logger.warning("Webhook de Mercado Pago con firma inválida")
        raise HTTPException(status_code=400, detail="Firma inválida")

    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}

    topic = request.query_params.get("type") or request.query_params.get("topic") or body.get("type")
    # 200 para todo lo que no es un pago utilizable: MP reintenta cualquier
    # respuesta != 2xx, y un evento que no manejamos no es un error.
    if topic != "payment" or not data_id.isalnum():
        return {"received": True}

    # Nunca se confia en el cuerpo de la notificacion para el estado o el
    # monto: se le pregunta a MP por el pago con el access token propio.
    try:
        payment = await mercadopago.get_payment(data_id)
    except Exception:
        # != 2xx a proposito: MP reintenta y la compra no se pierde por una
        # caida momentanea de su API.
        logger.exception("Fallo consultando el pago %s en Mercado Pago", data_id)
        raise HTTPException(status_code=502, detail="No se pudo consultar el pago")

    if payment is None:
        # Tipico del "simular notificacion" del panel de MP, con un id falso.
        logger.info("Notificación de Mercado Pago de un pago inexistente: %s", data_id)
        return {"received": True}

    await _grant_mercadopago_payment(db, payment)
    return {"received": True}


def _mercadopago_purchase_target(payment: dict) -> tuple[Optional[str], Optional[str]]:
    user_id, _, module_key = (payment.get("external_reference") or "").partition(":")
    if user_id and module_key:
        return user_id, module_key
    metadata = payment.get("metadata") or {}
    return metadata.get("user_id"), metadata.get("module_key")


async def _grant_mercadopago_payment(db: AsyncSession, payment: dict) -> None:
    # Fail-closed como en Stripe: pendiente (efectivo, transferencia sin
    # acreditar), rechazado o un estado ausente/desconocido no es una compra.
    if payment.get("status") != "approved":
        logger.info(
            "Pago de Mercado Pago %s sin aprobar (%s)", payment.get("id"), payment.get("status")
        )
        return

    user_id, module_key = _mercadopago_purchase_target(payment)
    if not user_id or not module_key:
        logger.warning("Pago de Mercado Pago sin compra identificable: %s", payment.get("id"))
        return
    # Un user_id que no existe romperia la FK en Postgres y el 500 haria que MP
    # reintente para siempre.
    if await db.get(User, user_id) is None:
        logger.warning("Pago de Mercado Pago %s de un usuario inexistente", payment.get("id"))
        return

    amount = payment.get("transaction_amount")
    currency = payment.get("currency_id")
    await ModulesService(db).grant(
        user_id=user_id,
        module_key=module_key,
        # MP informa el monto en unidades; se guarda en centavos como el resto.
        amount_paid=round(float(amount) * 100) if amount is not None else None,
        currency=currency.lower() if currency else None,
        stripe_session_id=str(payment.get("id")),
    )
