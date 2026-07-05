# FastAPI  Template

Production-ready, domain-first FastAPI template for large, scalable projects.

## Features

- **Domain-first structure** — each domain (`app/users`, `app/auth`, …) owns its router → service → repository → models layers, like Django apps. Adding a domain = adding one folder.
- **SQLAlchemy 2.0 async** + asyncpg, typed `Mapped[]` models, Alembic (async template) migrations
- **JWT auth** with access/refresh token pair — PyJWT + pwdlib (Argon2id). No python-jose, no passlib (both unmaintained / CVE-affected)
- **Taskiq** background tasks — `RedisStreamBroker` (acked delivery), separate worker & scheduler processes, FastAPI-style DI inside tasks
- **Observability** — structlog (JSON in prod, pretty console in dev) with request-id correlation, Prometheus `/metrics`, provisioned Grafana, optional Sentry
- **Rate limiting** — slowapi, Redis-backed in prod
- **Pagination** — fastapi-pagination (`Page[T]`)
- **Deployment** — multi-stage Dockerfile (uv, non-root), docker-compose with Traefik v3 (automatic Let's Encrypt HTTPS)
- **CI/CD** — GitHub Actions: lint + type-check + tests on every PR; image build to GHCR + SSH deploy to VPS on main
- **Tooling** — uv, ruff, mypy (pydantic plugin), pre-commit, Makefile

## Quickstart

```bash
cp example.env .env          # then edit SECRET_KEY at minimum
make db                      # postgres :5435 + redis :6380 (docker)
uv sync                      # install dependencies
make migrate                 # apply migrations
make seed                    # create first superuser (from FIRST_SUPERUSER_*)
make dev                     # http://127.0.0.1:8000/docs
```

## Project structure

```
app/
├── main.py            # app factory: middleware, routers, /api/v1 prefixes
├── core/              # config, security (JWT/hash), logging, exceptions, rate limit
├── db/                # engine, session-per-request, TimestampedBase, model registry
├── common/            # shared schemas + generic BaseRepository[T]
├── middleware.py      # request-id → structlog context
├── auth/              # domain: register / login / refresh + get_current_user
├── users/             # domain: model, schemas, repository, service, router, tasks
├── health/            # GET /api/v1/health (DB + Redis ping)
└── tasks/             # taskiq broker + scheduler entrypoints
migrations/            # alembic (async)
scripts/seed.py        # idempotent superuser seed
tests/                 # pytest, savepoint-rollback DB fixtures, httpx AsyncClient
deployment/            # Dockerfile, prod compose (Traefik v3, Prometheus, Grafana)
.github/workflows/     # ci.yml, cd.yml
docs/                  # 🇺🇿 Uzbek guides (Django comparisons)
```

## Make targets

| Target | What it does |
|---|---|
| `make db` | start dev Postgres (:5435) + Redis (:6380) |
| `make dev` | run uvicorn with hot reload |
| `make migrate` | `alembic upgrade head` |
| `make makemigration m="msg"` | autogenerate a migration |
| `make seed` | create first superuser from env |
| `make test` | run pytest |
| `make lint` | ruff check + format check + mypy |
| `make format` | auto-fix with ruff |
| `make worker` | run taskiq worker |
| `make scheduler` | run taskiq scheduler |

## Testing

```bash
make db && make test
```

Tests run against a separate `app_test` database (created automatically). Each
test runs inside a savepoint that is rolled back — no state leaks between tests.

## Background tasks

```bash
make worker      # consumes tasks from Redis stream
make scheduler   # fires cron-labeled tasks
```

In tests the broker is swapped for `InMemoryBroker`, so `.kiq()` executes inline.

## Deployment

See [deployment/README.md](deployment/README.md). Short version: copy
`deployment/` to the VPS, fill `.env`, `docker compose up -d`. Traefik v3
terminates TLS with automatic Let's Encrypt certificates.

## CI/CD

`ci.yml` runs ruff + mypy + pytest (with Postgres/Redis services) on every PR
and push to main. `cd.yml` runs after CI succeeds on main: builds the image,
pushes to GHCR, then deploys over SSH. Required repository secrets:

| Secret | Purpose |
|---|---|
| `VPS_HOST` | server address |
| `VPS_USER` | ssh user |
| `VPS_SSH_KEY` | private key (deploy key) |
| `API_DOMAIN` | domain for post-deploy health check |

