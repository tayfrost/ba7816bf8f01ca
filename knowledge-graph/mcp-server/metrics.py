"""
Prometheus metrics for the kg-mcp-server.

Since this is a FastMCP/SSE server (not HTTP), we run the prometheus
metrics endpoint on a separate port (9102).
"""

import time
import functools

from prometheus_client import Counter, Histogram, Gauge, start_http_server

SERVICE_NAME = "kg-mcp-server"
METRICS_PORT = 9102

# -- standard-ish request metrics --

http_requests_total = Counter(
    "http_requests_total",
    "Total MCP tool calls",
    ["method", "endpoint", "status_code", "service"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "MCP tool call duration",
    ["method", "endpoint", "service"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "MCP tool calls currently running",
    ["method", "service"],
)

# -- knowledge graph specific --

kg_queries_total = Counter(
    "kg_queries_total",
    "Total knowledge graph queries",
    ["query_type", "status"],
)

kg_query_duration_seconds = Histogram(
    "kg_query_duration_seconds",
    "Knowledge graph query duration",
    ["query_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)


def track_kg_query(query_type, status, duration):
    kg_queries_total.labels(query_type=query_type, status=status).inc()
    kg_query_duration_seconds.labels(query_type=query_type).observe(duration)


def track_tool_call(tool_name):
    """Decorator for MCP tool functions. Tracks call count, duration, in-progress."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            endpoint = f"/tool/{tool_name}"
            http_requests_in_progress.labels(method="TOOL", service=SERVICE_NAME).inc()
            start = time.perf_counter()
            status = "ok"
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start
                code = "200" if status == "ok" else "500"
                http_requests_total.labels(
                    method="TOOL", endpoint=endpoint,
                    status_code=code, service=SERVICE_NAME,
                ).inc()
                http_request_duration_seconds.labels(
                    method="TOOL", endpoint=endpoint, service=SERVICE_NAME,
                ).observe(duration)
                http_requests_in_progress.labels(method="TOOL", service=SERVICE_NAME).dec()
                # also track as kg query
                track_kg_query(tool_name, status, duration)
        return wrapper
    return decorator


def start_metrics_server():
    """Start prometheus metrics on a separate port. Call once at startup."""
    print(f"prometheus metrics on :{METRICS_PORT}/metrics")
    start_http_server(METRICS_PORT)
