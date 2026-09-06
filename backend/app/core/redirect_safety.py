"""Validacion de redirects hacia la app movil (deep links).

Varios flujos (login con Google, checkout de Stripe) reciben del cliente una
URL a la que volver una vez terminado el paso externo. Sin validar esa URL,
el endpoint seria un open redirect: cualquiera podria armar un link que abuse
del flujo para mandar a la victima, con datos sensibles en la query string, a
un sitio de phishing.
"""

from fastapi import HTTPException

ALLOWED_APP_REDIRECT_SCHEMES = (
    "exp://",
    "vidapersonal://",
    "http://localhost",
    "http://127.0.0.1",
    # La web de desarrollo (Vite, puerto 5173) ya queda cubierta por el
    # prefijo genérico "http://localhost" de arriba (coincide sin importar
    # el puerto), asi que no hace falta una entrada aparte para ella.
    # TODO: agregar dominio de producción real cuando exista.
)


def validate_app_redirect(app_redirect: str) -> None:
    if not app_redirect.startswith(ALLOWED_APP_REDIRECT_SCHEMES):
        raise HTTPException(status_code=400, detail="app_redirect invalido")
