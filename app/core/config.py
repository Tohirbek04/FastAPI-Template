from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Barcha konfiguratsiya env'dan (Django settings.py ekvivalenti)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    secret_key: str

    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 7

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    backend_cors_origins: list[str] = []
    sentry_dsn: str = ""

    first_superuser_email: str = ""
    first_superuser_password: str = ""

    @property
    def taskiq_broker_url(self) -> str:
        return self._redis_db(1)

    @property
    def taskiq_result_url(self) -> str:
        return self._redis_db(2)

    def _redis_db(self, db: int) -> str:
        parts = urlsplit(self.redis_url)
        return urlunsplit(parts._replace(path=f"/{db}"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
