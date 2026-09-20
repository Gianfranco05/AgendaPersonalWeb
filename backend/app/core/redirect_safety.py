"""Validacion de redirects hacia la app movil (deep links).

Varios flujos (login con Google, checkout de Stripe) reciben del cliente una
URL a la que volver una vez terminado el paso externo. Sin validar esa URL,
el endpoint seria un open redirect: cualquiera podria armar un link que abuse
del flujo para mandar a la victima, con datos sensibles en la query string, a
un sitio de phishing.
"""

from fastapi import HTTPException

from app.config import settings

# Esquemas fijos: el deep link de la app mobile (Expo Go en dev, el scheme
# propio en un build real) y localhost para probar la web en desarrollo.
_STATIC_ALLOWED_SCHEMES = (
    "exp://",
    "vidapersonal://",
    "http://localhost",
    "http://127.0.0.1",
    # La web de desarrollo (Vite, puerto 5173) ya queda cubierta por el
    # prefijo genérico "http://localhost" de arriba (coincide sin importar
    # el puerto), asi que no hace falta una entrada aparte para ella.
)


def _allowed_schemes() -> tuple[str, ...]:
    # settings.PUBLIC_BASE_URL es la unica fuente de verdad del dominio real
    # de produccion (ya se usa para armar links de mail y URLs de Stripe) —
    # se deriva de ahi en vez de mantener una whitelist separada a mano, que
    # quedaria desactualizada apenas cambie el dominio o se agregue uno nuevo.
    return _STATIC_ALLOWED_SCHEMES + (settings.PUBLIC_BASE_URL,)


def validate_app_redirect(app_redirect: str) -> None:
    if not app_redirect.startswith(_allowed_schemes()):
        raise HTTPException(status_code=400, detail="app_redirect invalido")
