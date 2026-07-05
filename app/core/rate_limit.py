from slowapi import Limiter
from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    """Haqiqiy klient IP.

    X-Forwarded-For bu yerda ataylab o'qilmaydi — header spoofing bilan
    rate-limit'ni aylanib o'tish mumkin bo'lardi. Buning o'rniga prod'da
    uvicorn `--proxy-headers --forwarded-allow-ips` bilan ishga tushiriladi
    (deployment/docker-compose.yml) va request.client allaqachon Traefik
    yozgan haqiqiy IP bo'ladi.
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
