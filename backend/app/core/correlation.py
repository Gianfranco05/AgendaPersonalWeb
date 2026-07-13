import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return correlation_id_var.get()


def set_correlation_id(value: str) -> None:
    correlation_id_var.set(value)


class CorrelationMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(corr_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
