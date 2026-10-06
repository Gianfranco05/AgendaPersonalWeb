"""Validacion de redirects hacia la app movil (deep links).

Varios flujos (login con Google, checkout) reciben del cliente una URL a la que
volver una vez terminado el paso externo. Sin validar esa URL, el endpoint
seria un open redirect: cualquiera podria armar un link que abuse del flujo
para mandar a la victima, con datos sensibles en la query string, a un sitio
de phishing. En el login con Google esos datos son los tokens de sesion: un
redirect aceptado de mas es robo de cuenta.
"""

from urllib.parse import urlsplit

from fastapi import HTTPException

from app.config import settings

# Scheme propio de la app (build de EAS). Cualquier ruta es valida: el scheme
# solo lo puede registrar la app con el package com.cancen.app.
_APP_SCHEME = "cancen"

# Solo fuera de produccion: Expo Go (exp://<host>:<puerto>) carga JS de
# cualquier host, asi que en prod aceptarlo dejaria que un bundle ajeno reciba
# los tokens; y localhost es la web de desarrollo en cualquier puerto.
_DEV_SCHEME = "exp"
_DEV_HOSTS = {"localhost", "127.0.0.1"}


def _is_allowed(app_redirect: str) -> bool:
    try:
        url = urlsplit(app_redirect)
        # .port valida el puerto: uno invalido levanta ValueError.
        url.port
    except ValueError:
        return False

    scheme = url.scheme.lower()
    if scheme == _APP_SCHEME:
        return True

    dev = not settings.is_production
    if scheme == _DEV_SCHEME:
        return dev

    if scheme not in ("http", "https") or url.username or url.password:
        return False

    # Se compara el origen exacto (scheme + host + puerto), no un prefijo:
    # "https://dominio.com.atacante.com" o "http://localhost.atacante.com"
    # empiezan igual que los permitidos.
    if dev and scheme == "http" and url.hostname in _DEV_HOSTS:
        return True

    base = urlsplit(settings.PUBLIC_BASE_URL)
    return (scheme, url.hostname, url.port) == (
        base.scheme.lower(),
        base.hostname,
        base.port,
    )


def validate_app_redirect(app_redirect: str) -> None:
    if not _is_allowed(app_redirect):
        raise HTTPException(status_code=400, detail="app_redirect invalido")
