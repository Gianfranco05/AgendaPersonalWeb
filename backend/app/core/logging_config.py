import logging
import os

from pythonjsonlogger import jsonlogger

from app.core.correlation import get_correlation_id


class CorrelationIdFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s %(correlation_id)s",
        timestamp=True,
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
