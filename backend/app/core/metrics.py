import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method"],
)

EXCLUDED_PATHS = {"/metrics"}


class PrometheusMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        method = request.method
        http_requests_in_progress.labels(method=method).inc()

        start = time.monotonic()
        try:
            response = await call_next(request)
        except BaseException:
            http_requests_total.labels(method=method, path=request.url.path, status=500).inc()
            raise
        finally:
            http_requests_in_progress.labels(method=method).dec()

        duration = time.monotonic() - start
        status = response.status_code
        path = request.url.path

        http_requests_total.labels(method=method, path=path, status=status).inc()
        http_request_duration_seconds.labels(method=method, path=path, status=status).observe(duration)

        return response
