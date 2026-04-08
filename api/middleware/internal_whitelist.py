"""
Middleware that restricts /internal/* routes to Docker-internal and loopback IPs.
On the production setup all internal callers (ai_service, webhooks) are
co-located in the same Docker Compose network (172.16.0.0/12), so external
traffic will always be rejected at this layer.
"""

import ipaddress
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_ALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),    # loopback
    ipaddress.ip_network("10.0.0.0/8"),     # Docker overlay / custom networks
    ipaddress.ip_network("172.16.0.0/12"),  # Docker default bridge (172.17–172.31.x.x)
    ipaddress.ip_network("192.168.0.0/16"), # host-mode or custom private ranges
]


def _is_internal(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _ALLOWED_NETWORKS)
    except ValueError:
        return False


class InternalWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/internal"):
            client_ip = request.client.host if request.client else None
            if not client_ip or not _is_internal(client_ip):
                logger.warning(
                    f"Blocked /internal request from {client_ip} — {request.method} {request.url.path}"
                )
                return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return await call_next(request)
