import re
import time

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

SERVICE_NAME = "payments"

# --- prometheus metrics ---

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "service"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "service"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Requests currently being processed",
    ["method", "service"],
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "Request body size",
    ["method", "endpoint", "service"],
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "Response body size",
    ["method", "endpoint", "service"],
)

_ID_PATTERN = re.compile(
    r"/([0-9]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)


def normalise_path(path):
    """Collapse numeric IDs and UUIDs so we don't blow up prometheus cardinality."""
    return _ID_PATTERN.sub("/{id}", path)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = normalise_path(request.url.path)

        http_requests_in_progress.labels(method=method, service=SERVICE_NAME).inc()

        body = await request.body()
        http_request_size_bytes.labels(
            method=method, endpoint=path, service=SERVICE_NAME
        ).observe(len(body))

        status_code = 500
        resp_size = 0
        start = time.perf_counter()

        try:
            resp = await call_next(request)
            status_code = resp.status_code

            resp_body = b""
            async for chunk in resp.body_iterator:
                resp_body += chunk if isinstance(chunk, bytes) else chunk.encode()
            resp_size = len(resp_body)

            return Response(
                content=resp_body,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.media_type,
            )
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start

            http_requests_total.labels(
                method=method, endpoint=path,
                status_code=str(status_code), service=SERVICE_NAME,
            ).inc()

            http_request_duration_seconds.labels(
                method=method, endpoint=path, service=SERVICE_NAME,
            ).observe(duration)

            http_response_size_bytes.labels(
                method=method, endpoint=path, service=SERVICE_NAME,
            ).observe(resp_size)

            http_requests_in_progress.labels(method=method, service=SERVICE_NAME).dec()


async def metrics_endpoint(request: Request):
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
