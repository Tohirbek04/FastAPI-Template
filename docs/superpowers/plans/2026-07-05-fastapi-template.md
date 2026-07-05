# FastAPI Production Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready, domain-first FastAPI template with JWT auth, Taskiq background tasks, full observability, Traefik v3 deployment, GitHub Actions CI/CD, and Uzbek educational docs.

**Architecture:** Domain-first packages (`app/auth`, `app/users`, `app/health`) over shared `app/core`, `app/db`, `app/common`. Each domain keeps its own router → service → repository → models layering. Async SQLAlchemy 2.0 + asyncpg with a session-per-request unit-of-work. One Docker image runs api/worker/scheduler behind Traefik v3.

**Tech Stack:** Python 3.12+, FastAPI ≥0.128, SQLAlchemy 2.0 (async) + asyncpg, Alembic (async), pydantic-settings v2, PyJWT, pwdlib[argon2], Taskiq (+taskiq-redis, +taskiq-fastapi), structlog, slowapi, fastapi-pagination, sentry-sdk, prometheus-fastapi-instrumentator, uv, ruff, mypy, pytest + pytest-asyncio + httpx.

**Spec:** `docs/superpowers/specs/2026-07-05-fastapi-template-design.md`

## Global Constraints

- Python ≥3.12. All env/deps via `uv` (`uv sync`, `uv run ...`). Never call pip directly.
- FORBIDDEN LIBRARIES: `python-jose` (CVE-2024-33663/33664), `passlib` (unmaintained, breaks with bcrypt≥4.1). Use PyJWT + pwdlib[argon2] only.
- Every function signature fully type-hinted (params + return).
- Async everywhere on the request path. `async_sessionmaker(..., expire_on_commit=False)`. No lazy loads — use `selectinload` when relationships appear.
- JWT decode MUST pin `algorithms=["HS256"]`.
- Secrets only via env (pydantic-settings). Never commit `.env`; `example.env` documents every variable.
- API version prefix `/api/v1` lives ONLY in `app/main.py` `include_router` calls; domain routers are version-agnostic.
- README.md in English; all `docs/*.md` guides in Uzbek, each comparing with Django.
- Tests require Postgres+Redis from `docker-compose.dev.yml` running (`make db`). pytest `asyncio_mode = "auto"`.
- Commit after each task with conventional commit messages. NEVER add `Co-Authored-By` lines.
- Run `make lint` (ruff + mypy) before every commit; it must pass.

---

### Task 1: Project scaffolding & tooling

**Files:**
- Delete: `main.py`, `test_main.http` (PyCharm leftovers)
- Create: `pyproject.toml`, `.gitignore`, `.dockerignore`, `example.env`, `Makefile`, `.pre-commit-config.yaml`, `docker-compose.dev.yml`, `app/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: `uv` environment with all runtime+dev deps; `make db|dev|test|lint|migrate|makemigration|seed|worker|scheduler` targets all later tasks rely on.

- [ ] **Step 1: Remove PyCharm leftovers**

```bash
rm main.py test_main.http
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "fastapi-template"
version = "0.1.0"
description = "Production-ready FastAPI template"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic[email]>=2.10.0",
    "pydantic-settings>=2.7.0",
    "pyjwt>=2.10.0",
    "pwdlib[argon2]>=0.2.1",
    "taskiq>=0.11.7",
    "taskiq-redis>=1.0.2",
    "taskiq-fastapi>=0.3.2",
    "redis>=5.2.0",
    "structlog>=24.4.0",
    "slowapi>=0.1.9",
    "fastapi-pagination>=0.12.32",
    "sentry-sdk[fastapi]>=2.20.0",
    "prometheus-fastapi-instrumentator>=7.0.0",
    "python-multipart>=0.0.20",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "pre-commit>=4.0.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["app", "tests", "scripts"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "ASYNC"]

[tool.mypy]
python_version = "3.12"
files = ["app", "scripts"]
disallow_untyped_defs = true
check_untyped_defs = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = ["slowapi.*", "taskiq_fastapi", "prometheus_fastapi_instrumentator.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.venv/
.env
.mypy_cache/
.pytest_cache/
.ruff_cache/
.idea/
.vscode/
htmlcov/
.coverage
dist/
*.egg-info/
letsencrypt/
```

- [ ] **Step 4: Write `.dockerignore`**

```
.venv
.git
.idea
.vscode
.env
__pycache__
.mypy_cache
.pytest_cache
.ruff_cache
tests
docs
.github
docker-compose.dev.yml
```

- [ ] **Step 5: Write `example.env`**

```bash
# Application
ENV=dev                          # dev | test | prod
DEBUG=true
SECRET_KEY=change-me-to-a-random-string-of-at-least-32-chars

# JWT
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=7

# Database / Redis
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5435/app
REDIS_URL=redis://localhost:6380/0

# CORS — JSON list; empty list disables the middleware
BACKEND_CORS_ORIGINS=[]

# Observability (empty = disabled)
SENTRY_DSN=

# Seed (make seed)
FIRST_SUPERUSER_EMAIL=admin@example.com
FIRST_SUPERUSER_PASSWORD=changeme123

# Deployment (used by deployment/docker-compose.yml)
DOMAIN=api.example.com
ACME_EMAIL=you@example.com
```

- [ ] **Step 6: Write `docker-compose.dev.yml`**

```yaml
services:
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5435:5432"
    volumes:
      - pgdata_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:8-alpine
    ports:
      - "6380:6379"

volumes:
  pgdata_dev:
```

- [ ] **Step 7: Write `Makefile`** (recipe lines MUST use tabs, not spaces)

```makefile
.PHONY: db dev migrate makemigration seed test lint format worker scheduler

db:
	docker compose -f docker-compose.dev.yml up -d

dev:
	uv run uvicorn app.main:app --reload

migrate:
	uv run alembic upgrade head

makemigration:
	uv run alembic revision --autogenerate -m "$(m)"

seed:
	uv run python scripts/seed.py

test:
	uv run pytest -v

lint:
	uv run ruff check . && uv run ruff format --check . && uv run mypy

format:
	uv run ruff check --fix . && uv run ruff format .

worker:
	uv run taskiq worker app.tasks.broker:broker

scheduler:
	uv run taskiq scheduler app.tasks.scheduler:scheduler
```

- [ ] **Step 8: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy
        language: system
        types: [python]
        pass_filenames: false
```

- [ ] **Step 9: Create package markers**

```bash
mkdir -p app tests
touch app/__init__.py tests/__init__.py
```

- [ ] **Step 10: Install and verify**

Run: `uv sync && make lint`
Expected: `uv sync` resolves deps, creates `uv.lock`; `make lint` passes.

Run: `make db && docker compose -f docker-compose.dev.yml ps`
Expected: postgres (healthy) and redis containers running.

Run: `uv run pre-commit install`
Expected: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding — uv, ruff, mypy, pytest, dev compose, Makefile"
```

---

### Task 2: Settings (`app/core/config.py`)

**Files:**
- Create: `app/core/__init__.py`, `app/core/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (BaseSettings) with fields `env: Literal["dev","test","prod"]`, `debug: bool`, `secret_key: str`, `access_token_ttl_min: int`, `refresh_token_ttl_days: int`, `database_url: str`, `redis_url: str`, `backend_cors_origins: list[str]`, `sentry_dsn: str`, `first_superuser_email: str`, `first_superuser_password: str`; properties `taskiq_broker_url: str` (redis db 1), `taskiq_result_url: str` (redis db 2); factory `get_settings() -> Settings` with `@lru_cache`.

- [ ] **Step 1: Write the failing test** — `tests/test_config.py`

```python
from app.core.config import Settings


def test_settings_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    settings = Settings()

    assert settings.env == "test"
    assert settings.database_url.endswith("/db")


def test_taskiq_urls_use_separate_redis_dbs(monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    settings = Settings()

    assert settings.taskiq_broker_url == "redis://localhost:6379/1"
    assert settings.taskiq_result_url == "redis://localhost:6379/2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core'`

- [ ] **Step 3: Write implementation** — empty `app/core/__init__.py` + `app/core/config.py`

```python
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Barcha konfiguratsiya env'dan (Django settings.py ekvivalenti)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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
        base, _, _ = self.redis_url.rpartition("/")
        return f"{base}/{db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Lint and commit**

```bash
make lint
git add app/core tests/test_config.py
git commit -m "feat: pydantic-settings configuration with cached factory"
```

---

### Task 3: Structured logging + request-context middleware

**Files:**
- Create: `app/core/logging.py`, `app/middleware.py`
- Test: `tests/test_logging.py`

**Interfaces:**
- Consumes: `get_settings()` (Task 2).
- Produces: `configure_logging() -> None`; `RequestContextMiddleware` (pure ASGI class) that clears structlog contextvars per request and binds `request_id` (from `X-Request-ID` header or new uuid4 hex) and `path`.

- [ ] **Step 1: Write the failing test** — `tests/test_logging.py`

```python
import structlog

from app.core.logging import configure_logging
from app.middleware import RequestContextMiddleware


def test_configure_logging_is_idempotent() -> None:
    configure_logging()
    configure_logging()
    structlog.get_logger().info("test_event", key="value")  # must not raise


async def test_middleware_binds_request_id() -> None:
    captured: dict[str, object] = {}

    async def inner_app(scope, receive, send) -> None:
        captured.update(structlog.contextvars.get_contextvars())

    middleware = RequestContextMiddleware(inner_app)
    scope = {
        "type": "http",
        "path": "/api/v1/health",
        "headers": [(b"x-request-id", b"req-123")],
    }

    async def receive():
        return {"type": "http.request"}

    async def send(message) -> None:
        return None

    await middleware(scope, receive, send)

    assert captured["request_id"] == "req-123"
    assert captured["path"] == "/api/v1/health"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logging.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/core/logging.py`**

```python
import logging

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Dev: rangli console; prod: JSON (Grafana/Loki uchun)."""
    settings = get_settings()
    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.env == "prod"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 4: Write `app/middleware.py`**

```python
import uuid

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestContextMiddleware:
    """Har request uchun structlog kontekstini tozalab, request_id bog'laydi."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        structlog.contextvars.clear_contextvars()
        headers = dict(scope["headers"])
        request_id = headers.get(b"x-request-id", uuid.uuid4().hex.encode()).decode()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=scope["path"])
        await self.app(scope, receive, send)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_logging.py -v`
Expected: 2 PASSED

- [ ] **Step 6: Lint and commit**

```bash
make lint
git add app/core/logging.py app/middleware.py tests/test_logging.py
git commit -m "feat: structlog config and request-context ASGI middleware"
```

---

### Task 4: Database layer (`app/db`)

**Files:**
- Create: `app/db/__init__.py`, `app/db/base.py`, `app/db/session.py`, `app/db/registry.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `get_settings()`.
- Produces: `Base` (AsyncAttrs + DeclarativeBase); `TimestampedBase` abstract model (UUID `id` pk, `created_at`, `updated_at`); `engine: AsyncEngine`; `SessionFactory: async_sessionmaker[AsyncSession]` (`expire_on_commit=False`); `get_db() -> AsyncIterator[AsyncSession]` that commits after a successful request; `app/db/registry.py` — imports every domain's models so Alembic autogenerate sees them.

**NOTE:** requires Postgres: run `make db` first.

- [ ] **Step 1: Write the failing test** — `tests/test_db.py`

```python
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5435/app")

from sqlalchemy import text  # noqa: E402

from app.db.base import TimestampedBase  # noqa: E402
from app.db.session import SessionFactory  # noqa: E402


async def test_engine_connects_and_selects() -> None:
    async with SessionFactory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


def test_timestamped_base_columns() -> None:
    assert hasattr(TimestampedBase, "id")
    assert hasattr(TimestampedBase, "created_at")
    assert hasattr(TimestampedBase, "updated_at")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Write `app/db/base.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TimestampedBase(Base):
    """Django'dagi umumiy BaseModel ekvivalenti: UUID pk + created/updated_at."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: Write `app/db/session.py`**

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(get_settings().database_url, echo=get_settings().debug)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Session-per-request unit of work: muvaffaqiyatda commit, xatoda rollback."""
    async with SessionFactory() as session:
        yield session
        await session.commit()
```

- [ ] **Step 5: Write `app/db/registry.py`** (and empty `app/db/__init__.py`)

```python
"""Alembic autogenerate va testlar uchun barcha modellarni import qiladi.

Yangi domen modeli qo'shilganda BU YERGA import qo'shing —
aks holda Alembic migratsiyada jadvalni ko'rmaydi.
"""
```

(The `User` import is added here in Task 6.)

- [ ] **Step 6: Run test to verify it passes**

Run: `make db && uv run pytest tests/test_db.py -v`
Expected: 2 PASSED

- [ ] **Step 7: Lint and commit**

```bash
make lint
git add app/db tests/test_db.py
git commit -m "feat: async SQLAlchemy engine, session dependency, timestamped base"
```

---

### Task 5: Exceptions + common schemas

**Files:**
- Create: `app/core/exceptions.py`, `app/common/__init__.py`, `app/common/schemas.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- Produces: `AppError(Exception)` with class attrs `status_code: int`, `code: str`, instance attr `detail: str`; subclasses `NotFoundError` (404, "not_found"), `ConflictError` (409, "conflict"), `UnauthorizedError` (401, "unauthorized"), `PermissionDeniedError` (403, "permission_denied"); `register_exception_handlers(app: FastAPI) -> None`; schemas `Msg(detail: str)`, `ErrorResponse(detail: str, code: str)`.

- [ ] **Step 1: Write the failing test** — `tests/test_exceptions.py`

```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    register_exception_handlers,
)


def test_error_hierarchy_attrs() -> None:
    assert NotFoundError.status_code == 404
    assert ConflictError.status_code == 409
    assert UnauthorizedError.status_code == 401
    assert PermissionDeniedError.status_code == 403
    err = NotFoundError("User not found")
    assert err.detail == "User not found"
    assert isinstance(err, AppError)


async def test_handler_converts_to_json() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise ConflictError("Email already registered")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered", "code": "conflict"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exceptions.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write `app/core/exceptions.py`**

```python
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class AppError(Exception):
    """Domain xatolari bazasi. Service qatlami HTTP'ni bilmaydi — shu xatolarni tashlaydi."""

    status_code = 500
    code = "app_error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.__name__
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("unhandled_app_error", code=exc.code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )
```

- [ ] **Step 4: Write `app/common/schemas.py`** (and empty `app/common/__init__.py`)

```python
from pydantic import BaseModel


class Msg(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    detail: str
    code: str
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_exceptions.py -v`
Expected: 2 PASSED

- [ ] **Step 6: Lint and commit**

```bash
make lint
git add app/core/exceptions.py app/common tests/test_exceptions.py
git commit -m "feat: domain error hierarchy with JSON handlers, common schemas"
```

---

### Task 6: User model + Alembic (async) + initial migration

**Files:**
- Create: `app/users/__init__.py`, `app/users/models.py`, `alembic.ini`, `migrations/` (via `alembic init -t async`), `migrations/versions/<hash>_create_users_table.py` (autogenerated)
- Modify: `app/db/registry.py` (import User), `migrations/env.py`
- Test: `tests/test_user_model.py`

**Interfaces:**
- Consumes: `TimestampedBase` from Task 4.
- Produces: `User` model — table `users`, columns `email: str (unique, indexed, 320)`, `hashed_password: str (255)`, `full_name: str (255, default "")`, `is_active: bool (default True)`, `is_superuser: bool (default False)` + inherited `id/created_at/updated_at`. Alembic configured: `make migrate` / `make makemigration m="msg"` work.

- [ ] **Step 1: Write the failing test** — `tests/test_user_model.py`

```python
from app.users.models import User


def test_user_model_definition() -> None:
    assert User.__tablename__ == "users"
    cols = {c.name for c in User.__table__.columns}
    assert {
        "id", "email", "hashed_password", "full_name",
        "is_active", "is_superuser", "created_at", "updated_at",
    } <= cols
    assert User.__table__.columns["email"].unique
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_user_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.users'`

- [ ] **Step 3: Write `app/users/models.py`** (and empty `app/users/__init__.py`)

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class User(TimestampedBase):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
```

- [ ] **Step 4: Register the model** — `app/db/registry.py` becomes:

```python
"""Alembic autogenerate va testlar uchun barcha modellarni import qiladi.

Yangi domen modeli qo'shilganda BU YERGA import qo'shing —
aks holda Alembic migratsiyada jadvalni ko'rmaydi.
"""

from app.users.models import User

__all__ = ["User"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_user_model.py -v`
Expected: PASSED

- [ ] **Step 6: Initialize Alembic with the async template**

```bash
uv run alembic init -t async migrations
```

- [ ] **Step 7: Edit `migrations/env.py`** — replace the generated `target_metadata = None` block with:

```python
from app.core.config import get_settings
from app.db import registry  # noqa: F401  — modellarni metadata'ga ro'yxatlaydi
from app.db.base import Base

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata
```

(Keep the rest of the async template as generated: `run_async_migrations` uses `async_engine_from_config` with `poolclass=pool.NullPool` and `connection.run_sync(do_run_migrations)`.)

Also in `alembic.ini`, comment out / remove the `sqlalchemy.url = ...` line (URL now comes from settings).

- [ ] **Step 8: Generate and apply the initial migration**

```bash
make db
uv run alembic revision --autogenerate -m "create users table"
```
Expected: new file `migrations/versions/<hash>_create_users_table.py` containing `op.create_table("users", ...)` with all 8 columns and a unique index on email. Inspect it before applying.

```bash
make migrate
docker compose -f docker-compose.dev.yml exec postgres psql -U app -d app -c "\d users"
```
Expected: `users` table exists with the expected columns.

- [ ] **Step 9: Lint and commit**

```bash
make lint
git add app/users app/db/registry.py alembic.ini migrations tests/test_user_model.py
git commit -m "feat: User model with async Alembic setup and initial migration"
```

---

### Task 7: Security — JWT + password hashing (`app/core/security.py`)

**Files:**
- Create: `app/core/security.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Consumes: `get_settings()`, `UnauthorizedError`.
- Produces: `hash_password(password: str) -> str`; `verify_password(password: str, hashed: str) -> bool`; `TokenType = Literal["access", "refresh"]`; `create_token(sub: str, token_type: TokenType) -> str`; `decode_token(token: str, expected_type: TokenType) -> dict[str, Any]` (raises `UnauthorizedError` on any invalid/expired/wrong-type token).

- [ ] **Step 1: Write the failing test** — `tests/test_security.py`

```python
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5435/app")

import jwt  # noqa: E402
import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.exceptions import UnauthorizedError  # noqa: E402
from app.core.security import (  # noqa: E402
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret-password")
    assert hashed != "secret-password"
    assert hashed.startswith("$argon2")
    assert verify_password("secret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_token_roundtrip() -> None:
    token = create_token("user-id-123", "access")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == "access"


def test_wrong_token_type_rejected() -> None:
    refresh = create_token("user-id-123", "refresh")
    with pytest.raises(UnauthorizedError):
        decode_token(refresh, expected_type="access")


def test_tampered_token_rejected() -> None:
    forged = jwt.encode({"sub": "x", "type": "access"}, "other-key", algorithm="HS256")
    with pytest.raises(UnauthorizedError):
        decode_token(forged, expected_type="access")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_security.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/core/security.py`**

```python
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

password_hash = PasswordHash.recommended()  # Argon2id

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(sub: str, token_type: TokenType) -> str:
    settings = get_settings()
    ttl = (
        timedelta(minutes=settings.access_token_ttl_min)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_ttl_days)
    )
    now = datetime.now(UTC)
    payload = {"sub": sub, "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=["HS256"]
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")
    return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_security.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Lint and commit**

```bash
make lint
git add app/core/security.py tests/test_security.py
git commit -m "feat: JWT tokens (PyJWT) and Argon2id password hashing (pwdlib)"
```

---

### Task 8: Test infrastructure (conftest) + BaseRepository + UserRepository

**Files:**
- Create: `tests/conftest.py`, `app/common/repository.py`, `app/users/repository.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Consumes: `Base`, `User`, `hash_password`.
- Produces:
  - Fixtures: `engine` (session-scoped AsyncEngine with schema created), `db_session` (function-scoped `AsyncSession` inside a savepoint — everything rolls back per test), `user_factory` (async callable: `await user_factory(email=..., password=..., **model_kwargs) -> User`).
  - `BaseRepository[ModelT: Base]` with `model: type[ModelT]` class attr, `__init__(self, session: AsyncSession)`, methods `get(obj_id: uuid.UUID) -> ModelT | None`, `create(**data: Any) -> ModelT` (flush, no commit), `update(obj: ModelT, **data: Any) -> ModelT`, `delete(obj: ModelT) -> None`.
  - `UserRepository(BaseRepository[User])` with `get_by_email(email: str) -> User | None`.

**IMPORTANT:** `tests/conftest.py` sets test env vars BEFORE importing any `app.*` module — module-level `engine` in `app/db/session.py` reads settings at import time. After adding conftest, DELETE the `os.environ` lines at the top of `tests/test_db.py` and `tests/test_security.py` (conftest now provides them); keep their remaining imports at top of file normally (no more `# noqa: E402`).

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import os

os.environ["ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5435/app_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import registry  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.users.models import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def _create_test_database() -> None:
    """app_test bazasini yaratadi (mavjud bo'lmasa)."""
    admin_url = get_settings().database_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = 'app_test'")
        )
        if not exists:
            await conn.execute(text("CREATE DATABASE app_test"))
    await admin_engine.dispose()


@pytest.fixture(scope="session")
async def engine(_create_test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Har test o'z savepoint'ida ishlaydi — oxirida hammasi rollback bo'ladi."""
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await conn.rollback()


@pytest.fixture
def user_factory(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[User]]:
    async def _create(
        email: str = "user@example.com",
        password: str = "password123",
        **kwargs: Any,
    ) -> User:
        user = User(email=email, hashed_password=hash_password(password), **kwargs)
        db_session.add(user)
        await db_session.flush()
        return user

    return _create
```

- [ ] **Step 2: Clean up earlier tests** — remove the `os.environ` header lines (and now-unneeded `# noqa: E402`) from `tests/test_db.py` and `tests/test_security.py`. `tests/test_db.py`'s `test_engine_connects_and_selects` now runs against `app_test` — that's fine.

Run: `uv run pytest -v`
Expected: all existing tests still PASS.

- [ ] **Step 3: Write the failing repository test** — `tests/test_repository.py`

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.users.repository import UserRepository


async def test_create_and_get(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="a@example.com", hashed_password="x")
    assert user.id is not None

    found = await repo.get(user.id)
    assert found is not None
    assert found.email == "a@example.com"


async def test_get_by_email(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    await repo.create(email="b@example.com", hashed_password="x")

    assert (await repo.get_by_email("b@example.com")) is not None
    assert (await repo.get_by_email("missing@example.com")) is None


async def test_update_and_delete(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="c@example.com", hashed_password="x")

    updated = await repo.update(user, full_name="New Name")
    assert updated.full_name == "New Name"

    await repo.delete(user)
    assert (await repo.get(user.id)) is None


async def test_get_missing_returns_none(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    assert (await repo.get(uuid.uuid4())) is None
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.users.repository'`

- [ ] **Step 5: Write `app/common/repository.py`**

```python
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[ModelT: Base]:
    """Django'dagi Model.objects manager'ining ekvivalenti — lekin explicit dependency."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def create(self, **data: Any) -> ModelT:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: ModelT, **data: Any) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
```

- [ ] **Step 6: Write `app/users/repository.py`**

```python
from sqlalchemy import select

from app.common.repository import BaseRepository
from app.users.models import User


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/test_repository.py -v`
Expected: 4 PASSED

- [ ] **Step 8: Lint and commit**

```bash
make lint
git add tests/conftest.py tests/test_repository.py tests/test_db.py tests/test_security.py app/common/repository.py app/users/repository.py
git commit -m "feat: generic BaseRepository, UserRepository, savepoint test fixtures"
```

---

### Task 9: Schemas + AuthService

**Files:**
- Create: `app/users/schemas.py`, `app/auth/__init__.py`, `app/auth/schemas.py`, `app/auth/service.py`
- Test: `tests/test_auth_service.py`

**Interfaces:**
- Consumes: `UserRepository`, `create_token`, `decode_token`, `hash_password`, `verify_password`, `ConflictError`, `UnauthorizedError`.
- Produces:
  - `app/users/schemas.py`: `UserRead` (`from_attributes=True`; fields `id: uuid.UUID`, `email: EmailStr`, `full_name: str`, `is_active: bool`, `is_superuser: bool`, `created_at: datetime`), `UserUpdate` (`full_name: str | None`, `password: str | None` min 8 max 128).
  - `app/auth/schemas.py`: `RegisterRequest` (`email: EmailStr`, `password: str` min 8 max 128, `full_name: str = ""`), `TokenPair` (`access_token: str`, `refresh_token: str`, `token_type: str = "bearer"`), `RefreshRequest` (`refresh_token: str`).
  - `AuthService(session: AsyncSession)` with `register(email, password, full_name="") -> User`, `login(email, password) -> TokenPair`, `refresh(refresh_token: str) -> TokenPair`.

- [ ] **Step 1: Write the failing test** — `tests/test_auth_service.py`

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import decode_token


async def test_register_creates_user(db_session: AsyncSession) -> None:
    user = await AuthService(db_session).register("new@example.com", "password123")
    assert user.email == "new@example.com"
    assert user.hashed_password != "password123"


async def test_register_duplicate_email_conflicts(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("dup@example.com", "password123")
    with pytest.raises(ConflictError):
        await service.register("dup@example.com", "password123")


async def test_login_returns_token_pair(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    user = await service.register("login@example.com", "password123")

    pair = await service.login("login@example.com", "password123")

    assert decode_token(pair.access_token, "access")["sub"] == str(user.id)
    assert decode_token(pair.refresh_token, "refresh")["sub"] == str(user.id)


async def test_login_wrong_password_unauthorized(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("wrong@example.com", "password123")
    with pytest.raises(UnauthorizedError):
        await service.login("wrong@example.com", "bad-password")


async def test_refresh_rotates_tokens(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("rot@example.com", "password123")
    pair = await service.login("rot@example.com", "password123")

    new_pair = await service.refresh(pair.refresh_token)

    assert decode_token(new_pair.access_token, "access")


async def test_refresh_with_access_token_rejected(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("mix@example.com", "password123")
    pair = await service.login("mix@example.com", "password123")
    with pytest.raises(UnauthorizedError):
        await service.refresh(pair.access_token)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 3: Write `app/users/schemas.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
```

- [ ] **Step 4: Write `app/auth/schemas.py`** (and empty `app/auth/__init__.py`)

```python
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
```

- [ ] **Step 5: Write `app/auth/service.py`**

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPair
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.users.models import User
from app.users.repository import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def register(self, email: str, password: str, full_name: str = "") -> User:
        if await self.users.get_by_email(email):
            raise ConflictError("Email already registered")
        return await self.users.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            # Bir xil xabar — user enumeration hujumiga qarshi
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Inactive user")
        return self._token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self.users.get(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return self._token_pair(user.id)

    def _token_pair(self, user_id: uuid.UUID) -> TokenPair:
        return TokenPair(
            access_token=create_token(str(user_id), "access"),
            refresh_token=create_token(str(user_id), "refresh"),
        )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_auth_service.py -v`
Expected: 6 PASSED

- [ ] **Step 7: Lint and commit**

```bash
make lint
git add app/users/schemas.py app/auth tests/test_auth_service.py
git commit -m "feat: auth service with register/login/refresh and user schemas"
```

---

### Task 10: App assembly (`app/main.py`) + health domain + client fixture

**Files:**
- Create: `app/core/rate_limit.py`, `app/health/__init__.py`, `app/health/router.py`, `app/main.py`
- Modify: `tests/conftest.py` (add `client` fixture)
- Test: `tests/test_health.py`

**Interfaces:**
- Consumes: everything from Tasks 2–5.
- Produces:
  - `app/core/rate_limit.py`: `limiter: Limiter` (slowapi) — key func `client_ip` reads `X-Forwarded-For` first (Traefik ortida turadi), Redis storage in prod / `memory://` otherwise, disabled when `env == "test"`.
  - `app/main.py`: module-level `app = FastAPI(...)` built by `create_app()`; Sentry init BEFORE app creation; `lifespan` context manager (Taskiq startup is added in Task 13 — for now just `yield`); middleware order: `RequestContextMiddleware` → CORS (only if origins configured) → `SlowAPIASGIMiddleware`; `register_exception_handlers(app)`; health router at `/api/v1/health`; Prometheus instrumentator exposing `/metrics` (excluded from schema).
  - conftest `client` fixture: `httpx.AsyncClient` over `ASGITransport(app)` with `get_db` overridden to the test `db_session`.

- [ ] **Step 1: Write the failing test** — `tests/test_health.py`

```python
from httpx import AsyncClient


async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"detail": "ok"}


async def test_metrics_exposed(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests" in response.text or "process_" in response.text
```

- [ ] **Step 2: Add the `client` fixture to `tests/conftest.py`** (append at the end)

```python
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    from app.db.session import get_db
    from app.main import app

    async def _get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 4: Write `app/core/rate_limit.py`**

```python
from slowapi import Limiter
from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    """Traefik ortida haqiqiy IP X-Forwarded-For'da keladi."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_settings = get_settings()

limiter = Limiter(
    key_func=client_ip,
    default_limits=["100/minute"],
    storage_uri=_settings.redis_url if _settings.env == "prod" else "memory://",
    headers_enabled=True,
    enabled=_settings.env != "test",
)
```

- [ ] **Step 5: Write `app/health/router.py`** (and empty `app/health/__init__.py`)

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Msg
from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter()


@router.get("", response_model=Msg)
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> Msg:
    """DB va Redis'ga chin ping — load balancer/deploy health check uchun."""
    await db.execute(text("SELECT 1"))
    redis: Redis = Redis.from_url(get_settings().redis_url)
    try:
        await redis.ping()
    finally:
        await redis.aclose()
    return Msg(detail="ok")
```

- [ ] **Step 6: Write `app/main.py`**

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.health.router import router as health_router
from app.middleware import RequestContextMiddleware

settings = get_settings()
configure_logging()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="FastAPI Template", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    register_exception_handlers(app)

    app.add_middleware(SlowAPIASGIMiddleware)
    if settings.backend_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.backend_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router, prefix="/api/v1/health", tags=["health"])

    Instrumentator(excluded_handlers=["/metrics", "/api/v1/health"]).instrument(
        app
    ).expose(app, include_in_schema=False)

    return app


app = create_app()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest tests/test_health.py -v`
Expected: 2 PASSED

- [ ] **Step 8: Smoke-check the dev server**

Run: `make dev` (in background or a second terminal), then `curl -s http://127.0.0.1:8000/api/v1/health`
Expected: `{"detail":"ok"}`. Also `http://127.0.0.1:8000/docs` serves Swagger UI. Stop the server.

- [ ] **Step 9: Lint and commit**

```bash
make lint
git add app/core/rate_limit.py app/health app/main.py tests/conftest.py tests/test_health.py
git commit -m "feat: app factory with health check, rate limiter, metrics, sentry"
```

---

### Task 11: Auth HTTP layer — deps + router

**Files:**
- Create: `app/auth/deps.py`, `app/auth/router.py`
- Modify: `app/main.py` (include auth router)
- Test: `tests/test_auth_api.py`

**Interfaces:**
- Consumes: `AuthService`, `decode_token`, `UserRepository`, schemas from Task 9, `limiter`.
- Produces: `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")`; `get_current_user(...) -> User` dependency; alias `CurrentUser = Annotated[User, Depends(get_current_user)]`; routes `POST /api/v1/auth/register` (201, `UserRead`), `POST /api/v1/auth/login` (OAuth2 form, `TokenPair`), `POST /api/v1/auth/refresh` (`TokenPair`).

- [ ] **Step 1: Write the failing test** — `tests/test_auth_api.py`

```python
from httpx import AsyncClient


async def test_register_login_refresh_flow(client: AsyncClient) -> None:
    # register
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "flow@example.com"
    assert "hashed_password" not in response.json()

    # duplicate → 409
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert response.status_code == 409

    # login (OAuth2 form: username field carries the email)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "flow@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"

    # refresh
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_wrong_password_401(client: AsyncClient, user_factory) -> None:
    await user_factory(email="u1@example.com", password="password123")
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "u1@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


async def test_refresh_with_access_token_401(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "u2@example.com", "password": "password123"},
    )
    access = login.json()["access_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


async def test_short_password_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={"email": "u3@example.com", "password": "short"}
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth_api.py -v`
Expected: FAIL — 404s (routes not registered yet)

- [ ] **Step 3: Write `app/auth/deps.py`**

```python
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.users.models import User
from app.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_token(token, expected_type="access")
    user = await UserRepository(db).get(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
```

- [ ] **Step 4: Write `app/auth/router.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RefreshRequest, RegisterRequest, TokenPair
from app.auth.service import AuthService
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.users.schemas import UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,  # slowapi decorator talab qiladi
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await AuthService(db).register(data.email, data.password, data.full_name)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit("20/minute")
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    return await AuthService(db).login(form.username, form.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    return await AuthService(db).refresh(data.refresh_token)
```

- [ ] **Step 5: Register the router in `app/main.py`** — add import and include:

```python
from app.auth.router import router as auth_router
```

and inside `create_app()`, right after the health router line:

```python
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_auth_api.py -v`
Expected: 4 PASSED

- [ ] **Step 7: Lint and commit**

```bash
make lint
git add app/auth/deps.py app/auth/router.py app/main.py tests/test_auth_api.py
git commit -m "feat: auth endpoints — register, login, refresh with rate limits"
```

---

### Task 12: Users HTTP layer — service, router, pagination

**Files:**
- Create: `app/users/service.py`, `app/users/router.py`
- Modify: `app/main.py` (include users router + `add_pagination`)
- Test: `tests/test_users_api.py`

**Interfaces:**
- Consumes: `CurrentUser`, `UserRepository`, `UserRead`, `UserUpdate`, `hash_password`, `PermissionDeniedError`.
- Produces: `UserService(session)` with `update_profile(user: User, data: UserUpdate) -> User`; routes `GET /api/v1/users/me`, `PATCH /api/v1/users/me`, `GET /api/v1/users` (superuser-only, `Page[UserRead]`).

- [ ] **Step 1: Write the failing test** — `tests/test_users_api.py`

```python
from httpx import AsyncClient

from app.core.security import create_token
from app.users.models import User


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(str(user.id), 'access')}"}


async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, user_factory) -> None:
    user = await user_factory(email="me@example.com")
    response = await client.get("/api/v1/users/me", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_patch_me_updates_name_and_password(
    client: AsyncClient, user_factory
) -> None:
    user = await user_factory(email="patch@example.com", password="password123")

    response = await client.patch(
        "/api/v1/users/me",
        headers=auth_header(user),
        json={"full_name": "Yangi Ism", "password": "newpassword123"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Yangi Ism"

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "patch@example.com", "password": "newpassword123"},
    )
    assert login.status_code == 200


async def test_list_users_forbidden_for_regular(client: AsyncClient, user_factory) -> None:
    user = await user_factory(email="plain@example.com")
    response = await client.get("/api/v1/users", headers=auth_header(user))
    assert response.status_code == 403


async def test_list_users_paginated_for_superuser(
    client: AsyncClient, user_factory
) -> None:
    admin = await user_factory(email="admin@example.com", is_superuser=True)
    for i in range(3):
        await user_factory(email=f"u{i}@example.com")

    response = await client.get(
        "/api/v1/users", headers=auth_header(admin), params={"page": 1, "size": 2}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_users_api.py -v`
Expected: FAIL — 404s

- [ ] **Step 3: Write `app/users/service.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        values: dict[str, str] = {}
        if data.full_name is not None:
            values["full_name"] = data.full_name
        if data.password is not None:
            values["hashed_password"] = hash_password(data.password)
        if values:
            user = await self.repo.update(user, **values)
        return user
```

- [ ] **Step 4: Write `app/users/router.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.core.exceptions import PermissionDeniedError
from app.db.session import get_db
from app.users.models import User
from app.users.schemas import UserRead, UserUpdate
from app.users.service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await UserService(db).update_profile(current_user, data)
    return UserRead.model_validate(user)


@router.get("", response_model=Page[UserRead])
async def list_users(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Page[UserRead]:
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser required")
    # Doim deterministik order_by — aks holda Postgres tartibi barqaror emas
    return await paginate(db, select(User).order_by(User.created_at, User.id))
```

- [ ] **Step 5: Register in `app/main.py`** — add imports:

```python
from fastapi_pagination import add_pagination

from app.users.router import router as users_router
```

inside `create_app()` after the auth router line:

```python
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
```

and after the `Instrumentator(...)` line (routers bo'lgandan keyin):

```python
    add_pagination(app)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_users_api.py -v`
Expected: 5 PASSED. Note: `get_current_user` returning 401 for missing header comes from `OAuth2PasswordBearer` (FastAPI's own 401), the rest via `UnauthorizedError`.

- [ ] **Step 7: Full suite + lint + commit**

```bash
uv run pytest -v
make lint
git add app/users/service.py app/users/router.py app/main.py tests/test_users_api.py
git commit -m "feat: users endpoints — me, profile update, paginated admin list"
```

---

### Task 13: Taskiq — broker, scheduler, welcome task

**Files:**
- Create: `app/tasks/__init__.py`, `app/tasks/broker.py`, `app/tasks/scheduler.py`, `app/users/tasks.py`
- Modify: `app/auth/service.py` (enqueue welcome task on register), `app/main.py` (broker lifecycle in lifespan)
- Test: `tests/test_tasks.py`

**Interfaces:**
- Consumes: `get_settings()`.
- Produces: `broker: AsyncBroker` (RedisStreamBroker + RedisAsyncResultBackend in dev/prod; InMemoryBroker when `env == "test"`); `scheduler: TaskiqScheduler`; task `send_welcome_email(email: str) -> None` (logs `welcome_email_sent`). CLI entrypoints used by Makefile: `app.tasks.broker:broker`, `app.tasks.scheduler:scheduler`.

- [ ] **Step 1: Write the failing test** — `tests/test_tasks.py`

```python
import structlog
from httpx import AsyncClient

from app.users.tasks import send_welcome_email


async def test_send_welcome_email_logs() -> None:
    with structlog.testing.capture_logs() as logs:
        task = await send_welcome_email.kiq("hello@example.com")
        await task.wait_result(timeout=5)

    assert any(log["event"] == "welcome_email_sent" for log in logs)


async def test_register_enqueues_welcome_email(client: AsyncClient) -> None:
    with structlog.testing.capture_logs() as logs:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "task@example.com", "password": "password123"},
        )

    assert response.status_code == 201
    assert any(log["event"] == "welcome_email_sent" for log in logs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tasks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.tasks'`

- [ ] **Step 3: Write `app/tasks/broker.py`** (and empty `app/tasks/__init__.py`)

```python
import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.core.config import get_settings

_settings = get_settings()

broker: AsyncBroker
if _settings.env == "test":
    broker = InMemoryBroker()
else:
    # RedisStreamBroker — ack bilan: worker o'lsa ham task yo'qolmaydi
    broker = RedisStreamBroker(url=_settings.taskiq_broker_url).with_result_backend(
        RedisAsyncResultBackend(
            redis_url=_settings.taskiq_result_url, result_ex_time=3600
        )
    )

# Dotted path — circular import'ning oldini oladi
taskiq_fastapi.init(broker, "app.main:app")
```

- [ ] **Step 4: Write `app/tasks/scheduler.py`**

```python
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.tasks.broker import broker

scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])
```

- [ ] **Step 5: Write `app/users/tasks.py`**

```python
import structlog

from app.tasks.broker import broker

logger = structlog.get_logger()


@broker.task
async def send_welcome_email(email: str) -> None:
    """Namuna task. Real loyihada bu yerda email provider chaqiriladi.

    Cron misoli:  @broker.task(schedule=[{"cron": "0 3 * * *", "schedule_id": "daily"}])
    """
    logger.info("welcome_email_sent", email=email)
```

- [ ] **Step 6: Enqueue from `app/auth/service.py`** — in `register`, before `return`:

```python
    async def register(self, email: str, password: str, full_name: str = "") -> User:
        if await self.users.get_by_email(email):
            raise ConflictError("Email already registered")
        user = await self.users.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await send_welcome_email.kiq(user.email)
        return user
```

with import at top: `from app.users.tasks import send_welcome_email`

- [ ] **Step 7: Wire broker lifecycle in `app/main.py`** — replace the `lifespan` body:

```python
from app.tasks.broker import broker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # MUHIM: worker jarayonida qayta startup qilinmaydi — cheksiz rekursiya bo'lardi
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/test_tasks.py -v`
Expected: 2 PASSED

- [ ] **Step 9: Smoke-check the real worker** (Redis must be up)

Run: `ENV=dev uv run taskiq worker app.tasks.broker:broker --workers 1 &` then stop with Ctrl+C after it prints "Listening started".
Expected: worker boots without import errors.

- [ ] **Step 10: Full suite, lint, commit**

```bash
uv run pytest -v
make lint
git add app/tasks app/users/tasks.py app/auth/service.py app/main.py tests/test_tasks.py
git commit -m "feat: taskiq broker, scheduler and welcome-email task wired to register"
```

---

### Task 14: Seed script (first superuser)

**Files:**
- Create: `scripts/seed.py`
- Test: `tests/test_seed.py`

**Interfaces:**
- Consumes: `SessionFactory`, `UserRepository`, `hash_password`, `get_settings()`.
- Produces: `async def seed() -> None` — creates a superuser from `FIRST_SUPERUSER_EMAIL`/`FIRST_SUPERUSER_PASSWORD` env if it doesn't exist; idempotent; runnable via `make seed`.

- [ ] **Step 1: Write the failing test** — `tests/test_seed.py`

```python
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import get_settings
from app.users.models import User
from scripts.seed import seed


async def test_seed_creates_superuser_once(engine: AsyncEngine, monkeypatch) -> None:
    monkeypatch.setenv("FIRST_SUPERUSER_EMAIL", "root@example.com")
    monkeypatch.setenv("FIRST_SUPERUSER_PASSWORD", "rootpassword123")
    get_settings.cache_clear()
    try:
        await seed()
        await seed()  # idempotent — ikkinchi chaqiruv xato bermaydi

        async with AsyncSession(engine) as session:
            from app.users.repository import UserRepository

            user = await UserRepository(session).get_by_email("root@example.com")
            assert user is not None
            assert user.is_superuser
            # tozalash — seed haqiqiy commit qiladi
            await session.execute(delete(User).where(User.email == "root@example.com"))
            await session.commit()
    finally:
        get_settings.cache_clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'`

- [ ] **Step 3: Write `scripts/seed.py`** (create `scripts/__init__.py` empty as well)

```python
import asyncio

import structlog

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.users.repository import UserRepository

logger = structlog.get_logger()


async def seed() -> None:
    settings = get_settings()
    if not settings.first_superuser_email or not settings.first_superuser_password:
        logger.warning("seed_skipped", reason="FIRST_SUPERUSER_* env not set")
        return
    async with SessionFactory() as session:
        repo = UserRepository(session)
        if await repo.get_by_email(settings.first_superuser_email):
            logger.info("superuser_exists", email=settings.first_superuser_email)
            return
        await repo.create(
            email=settings.first_superuser_email,
            hashed_password=hash_password(settings.first_superuser_password),
            is_superuser=True,
        )
        await session.commit()
        logger.info("superuser_created", email=settings.first_superuser_email)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(seed())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seed.py -v`
Expected: PASSED

- [ ] **Step 5: Lint and commit**

```bash
make lint
git add scripts tests/test_seed.py
git commit -m "feat: idempotent superuser seed script"
```

---

### Task 15: Deployment — Dockerfile, prod compose (Traefik v3), Prometheus, Grafana

**Files:**
- Create: `deployment/Dockerfile`, `deployment/docker-compose.yml`, `deployment/prometheus/prometheus.yml`, `deployment/grafana/provisioning/datasources/prometheus.yml`, `deployment/README.md`

**Interfaces:**
- Consumes: the app image entrypoints — `uvicorn app.main:app`, `taskiq worker app.tasks.broker:broker`, `taskiq scheduler app.tasks.scheduler:scheduler`, `alembic upgrade head`.
- Produces: production stack `traefik + api + worker + scheduler + postgres + redis + prometheus + grafana`; image published as `ghcr.io/<owner>/<repo>` (CD task 16 pushes it).

- [ ] **Step 1: Write `deployment/Dockerfile`** (multi-stage, uv, non-root)

```dockerfile
# --- Stage 1: builder ---------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Avval faqat lock fayllar — dependency layer cache'lanadi
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# --- Stage 2: runtime ----------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Verify the image builds**

Run: `docker build -f deployment/Dockerfile -t fastapi-template:local .`
Expected: build succeeds. Then quick check: `docker run --rm fastapi-template:local python -c "import app.main"` — exits 0 IF env vars provided; instead run `docker run --rm -e SECRET_KEY=x -e DATABASE_URL=postgresql+asyncpg://u:p@h/db fastapi-template:local python -c "import app.main; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Write `deployment/docker-compose.yml`**

The server keeps a `.env` file NEXT TO this compose file (copy from `example.env`, set `ENV=prod`, real `SECRET_KEY`, `DOMAIN`, `ACME_EMAIL`, and container-internal URLs: `DATABASE_URL=postgresql+asyncpg://app:${POSTGRES_PASSWORD}@postgres:5432/app`, `REDIS_URL=redis://redis:6379/0`).

```yaml
services:
  traefik:
    image: traefik:v3.7
    restart: unless-stopped
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=web"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.le.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt
    networks:
      - web

  api:
    image: ${DOCKER_IMAGE:-ghcr.io/OWNER/fastapi-template:latest}
    restart: unless-stopped
    env_file: .env
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`${DOMAIN}`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=le"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
    networks:
      - web
      - internal

  worker:
    image: ${DOCKER_IMAGE:-ghcr.io/OWNER/fastapi-template:latest}
    restart: unless-stopped
    env_file: .env
    command: taskiq worker app.tasks.broker:broker
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - internal

  scheduler:
    image: ${DOCKER_IMAGE:-ghcr.io/OWNER/fastapi-template:latest}
    restart: unless-stopped
    env_file: .env
    command: taskiq scheduler app.tasks.scheduler:scheduler
    depends_on:
      redis:
        condition: service_started
    networks:
      - internal

  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - internal

  redis:
    image: redis:8-alpine
    restart: unless-stopped
    volumes:
      - redisdata:/data
    networks:
      - internal

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - promdata:/prometheus
    networks:
      - internal

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - grafanadata:/var/lib/grafana
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.${DOMAIN}`)"
      - "traefik.http.routers.grafana.entrypoints=websecure"
      - "traefik.http.routers.grafana.tls.certresolver=le"
      - "traefik.http.services.grafana.loadbalancer.server.port=3000"
    networks:
      - web
      - internal

networks:
  web:
  internal:

volumes:
  pgdata:
  redisdata:
  promdata:
  grafanadata:
  letsencrypt:
```

Add to `example.env` (append):

```bash
# Prod compose extras
POSTGRES_PASSWORD=strong-password-here
GRAFANA_ADMIN_PASSWORD=strong-password-here
DOCKER_IMAGE=ghcr.io/OWNER/fastapi-template:latest
```

- [ ] **Step 4: Write `deployment/prometheus/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: fastapi
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8000"]
```

- [ ] **Step 5: Write `deployment/grafana/provisioning/datasources/prometheus.yml`**

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

- [ ] **Step 6: Write `deployment/README.md`** — short English ops runbook:

```markdown
# Deployment

## First-time VPS setup
1. Install Docker + compose plugin.
2. `mkdir -p /opt/fastapi-template && cd /opt/fastapi-template`
3. Copy this `deployment/` directory to the server.
4. `cp example.env deployment/.env` and edit: `ENV=prod`, `DEBUG=false`, real
   `SECRET_KEY`, `POSTGRES_PASSWORD`, `DOMAIN`, `ACME_EMAIL`,
   `DATABASE_URL=postgresql+asyncpg://app:<POSTGRES_PASSWORD>@postgres:5432/app`,
   `REDIS_URL=redis://redis:6379/0`, `DOCKER_IMAGE=ghcr.io/<owner>/<repo>:latest`.
5. `cd deployment && docker compose up -d`

Traefik obtains Let's Encrypt certificates automatically (HTTP-01 challenge);
`acme.json` persists in the `letsencrypt` volume.

## Notes
- `/metrics` is NOT routed through Traefik — Prometheus scrapes it on the
  internal network only.
- Grafana lives at `https://grafana.<DOMAIN>` (provisioned Prometheus
  datasource; import a FastAPI dashboard, e.g. grafana.com ID 11713).
- Migrations run automatically before the api starts (`alembic upgrade head`).
  With >1 api replica, run migrations as a separate one-shot service instead.
```

- [ ] **Step 7: Validate compose file**

Run: `cd deployment && DOMAIN=example.com ACME_EMAIL=a@b.c POSTGRES_PASSWORD=x docker compose config >/dev/null && cd ..`
Expected: exits 0 (valid YAML + interpolation).

- [ ] **Step 8: Commit**

```bash
git add deployment example.env
git commit -m "feat: production deployment — Dockerfile, Traefik v3 compose, monitoring"
```

---

### Task 16: CI/CD — GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/cd.yml`

**Interfaces:**
- Consumes: `make`-equivalent commands (`uv run ruff/mypy/pytest`), `deployment/Dockerfile`, conftest's `TEST_DATABASE_URL` support.
- Produces: CI on every PR + main push; CD (build → GHCR → SSH deploy) only after CI succeeds on main. Required repo secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `API_DOMAIN`.

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: app_test
        ports:
          - "5432:5432"
        options: >-
          --health-cmd "pg_isready -U app"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 10
      redis:
        image: redis:8-alpine
        ports:
          - "6379:6379"
    env:
      TEST_DATABASE_URL: postgresql+asyncpg://app:app@localhost:5432/app_test
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy
      - run: uv run pytest -v
```

- [ ] **Step 2: Write `.github/workflows/cd.yml`**

```yaml
name: CD

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]

jobs:
  build:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: deployment/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.event.workflow_run.head_sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/fastapi-template/deployment
            docker compose pull
            docker compose up -d
            sleep 10
            curl -fsS https://${{ secrets.API_DOMAIN }}/api/v1/health
```

- [ ] **Step 3: Validate workflow YAML locally**

Run: `uv run python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]; print('ok')"`
Expected: `ok` (pyyaml sqlalchemy dep tree orqali mavjud; bo'lmasa `uvx yamllint .github/workflows` ishlating).

- [ ] **Step 4: Commit**

```bash
git add .github
git commit -m "ci: test pipeline and GHCR build + VPS deploy pipeline"
```

---

### Task 17: Documentation — English README + 8 Uzbek guides

**Files:**
- Create: `README.md`, `docs/01-structure.md`, `docs/02-config.md`, `docs/03-database.md`, `docs/04-auth.md`, `docs/05-background-tasks.md`, `docs/06-observability.md`, `docs/07-deployment.md`, `docs/08-cicd.md`

**Interfaces:**
- Consumes: the finished codebase — every guide references REAL file paths and code from this repo.

**Language rule:** `README.md` — English. All `docs/*.md` — Uzbek (lotin alifbosi). Every guide has a "Django'da bunday edi" section.

- [ ] **Step 1: Write `README.md`** (English) with these sections:
  - **Features** — bulleted stack summary (domain-first structure, SQLAlchemy 2.0 async, JWT auth via PyJWT+pwdlib, Taskiq, structlog, Prometheus/Grafana, Sentry, Traefik v3 deploy, GitHub Actions CI/CD).
  - **Quickstart** — exact commands: `cp example.env .env`, `make db`, `uv sync`, `make migrate`, `make seed`, `make dev`, open `http://127.0.0.1:8000/docs`.
  - **Project structure** — the `app/` tree from the spec with one-line English comments.
  - **Make targets** — table of all Makefile commands.
  - **Testing** — `make db && make test`.
  - **Background tasks** — `make worker`, `make scheduler`.
  - **Deployment** — pointer to `deployment/README.md`.
  - **CI/CD** — required GitHub secrets table (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `API_DOMAIN`).
  - **Docs** — note that `docs/` contains Uzbek guides for developers coming from Django.

- [ ] **Step 2: Write `docs/01-structure.md`** (Uzbek). Must cover:
  - Nega domen-birinchi: Django `apps/` bilan yonma-yon taqqoslash (`apps/users` ↔ `app/users`).
  - Har qatlam vazifasi jadvali: `router.py` ↔ views+urls, `service.py` ↔ biznes logika (Django'da ko'pincha view yoki model method ichida), `repository.py` ↔ `objects` manager, `models.py` ↔ models, `schemas.py` ↔ serializers, `deps.py` ↔ DRF permission/authentication classes.
  - Qoida: router faqat HTTP bilan ishlaydi; service HTTP'ni bilmaydi (domain exception tashlaydi); repository faqat query.
  - Yangi domen qo'shish bo'yicha qadam-baqadam checklist (papka yaratish → models → registry.py'ga import → makemigration → router'ni main.py'ga ulash).

- [ ] **Step 3: Write `docs/02-config.md`** (Uzbek). Must cover:
  - `settings.py` vs `pydantic-settings`: nega klass, nega env-first (12-factor).
  - `.env` / `example.env` oqimi; `SettingsConfigDict(env_file=".env", extra="ignore")` izohi.
  - `@lru_cache get_settings()` — nega har chaqiruvda qayta o'qilmaydi; testda `cache_clear()`.
  - Har bir env o'zgaruvchining ma'nosi jadvali (example.env'dagi barcha kalitlar).

- [ ] **Step 4: Write `docs/03-database.md`** (Uzbek). Must cover:
  - Django ORM ↔ SQLAlchemy 2.0 query taqqoslash jadvali, kamida: `User.objects.get(pk=x)` ↔ `session.get(User, x)`; `filter(email=..)` ↔ `select(User).where(...)`; `select_related` ↔ `selectinload`; `get_or_404` ↔ repository + `NotFoundError`; `update()` ↔ setattr+flush; `transaction.atomic()` ↔ session/`begin()`.
  - `expire_on_commit=False` va `MissingGreenlet` tuzog'i (lazy load async'da ishlamaydi).
  - Session-per-request `get_db` unit-of-work: qachon commit, qachon rollback.
  - Alembic ↔ makemigrations/migrate: `make makemigration m="..."`, `make migrate`; `app/db/registry.py` nima uchun kerak.

- [ ] **Step 5: Write `docs/04-auth.md`** (Uzbek). Must cover:
  - `django.contrib.auth` bilan farq: sessiya-cookie vs stateless JWT.
  - Access/refresh oqimi diagrammasi (matnli); nega refresh alohida `type` claim bilan.
  - Nega PyJWT (python-jose CVE'lari) va pwdlib/Argon2id (passlib o'lik) — versiya tarixi bilan.
  - `get_current_user` dependency ↔ DRF `IsAuthenticated`; superuser tekshiruvi ↔ `IsAdminUser`.
  - Xavfsizlik eslatmalari: `algorithms` pin, bir xil 401 xabari (user enumeration), parol min 8.

- [ ] **Step 6: Write `docs/05-background-tasks.md`** (Uzbek). Must cover:
  - Celery ↔ Taskiq jadvali: `@shared_task` ↔ `@broker.task`, `delay()` ↔ `kiq()`, beat ↔ `TaskiqScheduler` + cron label, `CELERY_BROKER_URL` ↔ `taskiq_broker_url`.
  - Nega RedisStreamBroker (ack — worker o'lsa task yo'qolmaydi).
  - `TaskiqDepends` bilan task ichida `get_db` olish misoli (kod bilan).
  - `broker.is_worker_process` lifespan tuzog'i izohi.
  - Ishga tushirish: `make worker`, `make scheduler`; prod'da alohida container'lar.

- [ ] **Step 7: Write `docs/06-observability.md`** (Uzbek). Must cover:
  - structlog: nega JSON prod'da; `request_id` correlation qanday ishlaydi (middleware → contextvars → har log yozuvi).
  - Sentry: DSN qo'yish yetarli; `traces_sample_rate` ma'nosi.
  - Prometheus: `/metrics` nima beradi; nega Traefik orqali chiqarilmaydi; Grafana'da dashboard import qilish.
  - Django taqqoslash: `LOGGING` dict ↔ `configure_logging()`; django-prometheus ↔ instrumentator.

- [ ] **Step 8: Write `docs/07-deployment.md`** (Uzbek). Must cover:
  - Arxitektura sxemasi (matnli): Internet → Traefik (443, TLS) → api; worker/scheduler ichki tarmoqda; ikki network (`web`/`internal`) nima uchun.
  - Dockerfile bosqichlari izohi (nega multi-stage, nega non-root, layer caching).
  - Traefik v3: label'lar qanday o'qiladi, ACME/Let's Encrypt oqimi, `exposedbydefault=false` xavfsizligi.
  - VPS'ga birinchi deploy checklist (deployment/README.md'ning o'zbekcha kengaytmasi).
  - Django template bilan farqlar: gunicorn+nginx ↔ uvicorn+traefik.

- [ ] **Step 9: Write `docs/08-cicd.md`** (Uzbek). Must cover:
  - CI oqimi qadam-baqadam: services (postgres/redis) qanday ko'tariladi, `TEST_DATABASE_URL` qayerdan keladi.
  - CD oqimi: `workflow_run` trigger nima uchun (CI yashil bo'lmaguncha deploy yo'q), GHCR image tag'lari, SSH deploy skripti.
  - Kerakli GitHub secrets jadvali va ularni qanday olish (`ssh-keygen`, deploy key).
  - Yangi loyihada sozlash checklist: repo yaratish → secrets qo'shish → `DOCKER_IMAGE` ni o'zgartirish → birinchi push.

- [ ] **Step 10: Verify docs**

Run: `ls docs/*.md | wc -l`
Expected: 8 (+ superpowers papkasi alohida). Each file non-empty; every referenced file path exists in the repo (spot-check with `ls`).

- [ ] **Step 11: Commit**

```bash
git add README.md docs
git commit -m "docs: English README and 8 Uzbek guides comparing with Django"
```

---

## Final Verification (after all tasks)

- [ ] `make db && uv run pytest -v` — full suite green.
- [ ] `make lint` — clean.
- [ ] `make dev` + `curl http://127.0.0.1:8000/api/v1/health` → `{"detail":"ok"}`; `/docs` opens.
- [ ] `docker build -f deployment/Dockerfile .` — succeeds.
- [ ] `cd deployment && docker compose config` — valid.
- [ ] Success criteria from spec section 13 all satisfied.



