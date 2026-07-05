from slowapi import Limiter
from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    """Real client IP.

    X-Forwarded-For is deliberately NOT read here — trusting it would let
    clients spoof the header and bypass rate limits. In production uvicorn
    runs with `--proxy-headers --forwarded-allow-ips` (see
    deployment/docker-compose.yml), so request.client already holds the
    real IP written by the reverse proxy.
    """
    return request.client.host if request.client else "unknown"


_settings = get_settings()

limiter = Limiter(
    key_func=client_ip,
    default_limits=["100/minute"],
    storage_uri=_settings.redis_url if _settings.env == "prod" else "memory://",
    headers_enabled=True,
    enabled=_settings.env != "test",
)
