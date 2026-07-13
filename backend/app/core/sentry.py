import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


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
    )
