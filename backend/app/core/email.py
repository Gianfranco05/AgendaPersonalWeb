"""Envio de mails transaccionales via Resend.

Se habla con la API HTTP directamente (httpx ya es dependencia) en vez de sumar
el SDK: es un solo POST y evita una dependencia mas que mantener.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


async def send_email(to: str, subject: str, html: str) -> bool:
    """Devuelve True si se envio. Nunca levanta: un mail caido no puede tirar
    abajo el registro ni el pedido de reset."""
    if not settings.RESEND_API_KEY:
        # Dev/test: sin API key no se manda nada, se deja rastro en el log para
        # poder seguir el flujo a mano.
        logger.info(
            "Email no enviado (RESEND_API_KEY vacio) | to=%s | subject=%s\n%s",
            to,
            subject,
            html,
        )
        return False

    payload = {
        "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                RESEND_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            )
            response.raise_for_status()
        return True
    except Exception:
        logger.exception("Fallo el envio de email a %s (subject=%s)", to, subject)
        return False


def _layout(title: str, body: str, cta_url: str, cta_label: str) -> str:
    return f"""\
<div style="font-family:system-ui,-apple-system,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1f2937">
  <h1 style="font-size:20px;margin:0 0 16px">{title}</h1>
  {body}
  <p style="margin:24px 0">
    <a href="{cta_url}"
       style="display:inline-block;background:#7C3AED;color:#fff;text-decoration:none;
              padding:12px 20px;border-radius:8px;font-weight:600">{cta_label}</a>
  </p>
  <p style="font-size:13px;color:#6b7280">
    Si el boton no funciona, copiá este link:<br>
    <span style="word-break:break-all">{cta_url}</span>
  </p>
</div>"""


async def send_verification_email(to: str, token: str) -> bool:
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/verificar-email?token={token}"
    html = _layout(
        title="Confirmá tu email",
        body=(
            "<p>Confirmá tu dirección para terminar de activar tu cuenta en "
            f"{settings.MAIL_FROM_NAME}.</p>"
            f"<p style='font-size:13px;color:#6b7280'>El link vence en "
            f"{settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS} horas.</p>"
        ),
        cta_url=url,
        cta_label="Confirmar email",
    )
    return await send_email(to, "Confirmá tu email", html)


async def send_password_reset_email(to: str, token: str) -> bool:
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/resetear-password?token={token}"
    html = _layout(
        title="Restablecer tu contraseña",
        body=(
            "<p>Pediste restablecer tu contraseña. Si no fuiste vos, ignorá este "
            "mail: tu contraseña actual sigue funcionando.</p>"
            f"<p style='font-size:13px;color:#6b7280'>El link vence en "
            f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hora(s).</p>"
        ),
        cta_url=url,
        cta_label="Elegir nueva contraseña",
    )
    return await send_email(to, "Restablecer tu contraseña", html)
