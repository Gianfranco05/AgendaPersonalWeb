"""Cliente minimo de Mercado Pago (Checkout Pro).

Se habla con la API HTTP directamente (httpx ya es dependencia) en vez de sumar
el SDK oficial: solo hacen falta dos llamadas, crear la preferencia y leer un
pago.
"""

import hashlib
import hmac
from typing import Optional

import httpx

from app.config import settings

MP_API_BASE = "https://api.mercadopago.com"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=MP_API_BASE,
        timeout=10.0,
        headers={"Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"},
    )


async def create_preference(payload: dict) -> dict:
    """Crea la preferencia de Checkout Pro. Lanza si MP no la acepta."""
    async with _client() as client:
        resp = await client.post("/checkout/preferences", json=payload)
    resp.raise_for_status()
    return resp.json()


async def get_payment(payment_id: str) -> Optional[dict]:
    """Pago tal como lo tiene Mercado Pago, o None si no existe.

    Lanza ante cualquier otro error: el webhook tiene que devolver != 2xx para
    que MP reintente, en vez de perder una compra por una caida momentanea.
    """
    async with _client() as client:
        resp = await client.get(f"/v1/payments/{payment_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _parse_signature_header(header: str) -> tuple[Optional[str], Optional[str]]:
    ts = v1 = None
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "ts":
            ts = value.strip()
        elif key == "v1":
            v1 = value.strip()
    return ts, v1


def verify_signature(
    x_signature: str, x_request_id: str, data_id: str, secret: str
) -> bool:
    """Valida el header x-signature de una notificacion de Mercado Pago.

    El manifest es `id:{data.id};request-id:{x-request-id};ts:{ts};`, firmado
    con HMAC-SHA256 usando la clave secreta del webhook. Segun la doc de MP,
    las partes que no vienen en la notificacion se omiten del template.
    """
    ts, v1 = _parse_signature_header(x_signature or "")
    if not ts or not v1:
        return False

    manifest = ""
    if data_id:
        # MP firma el id en minusculas cuando es alfanumerico.
        manifest += f"id:{data_id.lower()};"
    if x_request_id:
        manifest += f"request-id:{x_request_id};"
    manifest += f"ts:{ts};"

    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)
