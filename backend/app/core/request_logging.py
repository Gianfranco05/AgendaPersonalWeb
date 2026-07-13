import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "correlation_id": get_correlation_id(),
        }

        if response.status_code >= 500:
            logger.error("Request failed", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Request warning", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)

        return response
