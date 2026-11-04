import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


_SEARCH_PATH = "/api/v1/search"


def scrub_search_query(event, hint):
    """Saca el query string de los eventos de `/api/v1/search`.

    Los terminos de busqueda pueden ser sensibles (salud, plata) y Sentry
    adjunta `request.query_string` y la URL completa aunque `send_default_pii`
    sea False. Se usa como `before_send` y `before_send_transaction`.
    """
    request = event.get("request") if isinstance(event, dict) else None
    if not isinstance(request, dict):
        return event
    url = request.get("url") or ""
    if _SEARCH_PATH not in url.split("?", 1)[0]:
        return event
    request.pop("query_string", None)
    request["url"] = url.split("?", 1)[0]
    return event


def init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    environment = os.getenv("ENVIRONMENT", "development")
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
        send_default_pii=False,
        before_send=scrub_search_query,
        before_send_transaction=scrub_search_query,
    )
