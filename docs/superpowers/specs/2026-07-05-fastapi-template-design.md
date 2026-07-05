# FastAPI Production Template — Dizayn Spetsifikatsiyasi

**Sana:** 2026-07-05
**Maqsad:** Yirik, kengayuvchan FastAPI loyihalari uchun production-ready shablon. Django'dan kelgan dasturchi uchun har bir qism o'zbekcha qo'llanmalar bilan hujjatlashtiriladi.

## 1. Umumiy talablar

- Yirik loyihalarga mo'ljallangan: domen-birinchi struktura, gorizontal scale (stateless API, alohida worker'lar), aniq qatlam chegaralari.
- To'liq async stack (I/O-bound yo'nalish).
- `uv` bilan dependency boshqaruvi, `ruff` + `mypy` sifat nazorati.
- README inglizcha; `docs/` qo'llanmalari o'zbekcha (Django bilan taqqoslab).
- Sirlar faqat env orqali (`pydantic-settings`), `.env` commit qilinmaydi, `example.env` beriladi.

## 2. Texnologiyalar (context7 orqali tekshirilgan, 2026-07)

| Vazifa | Tanlov | Izoh / rad etilganlar |
|---|---|---|
| Framework | FastAPI 0.128+ | `lifespan` context manager (`on_event` deprecated) |
| ORM | SQLAlchemy 2.0 async, `Mapped[]`/`mapped_column` | `expire_on_commit=False`; lazy load o'rniga `selectinload` |
| DB drayver | asyncpg (PostgreSQL) | pgbouncer tx-pooling'da `statement_cache_size=0` eslatmasi docs'da |
| Migratsiya | Alembic (`alembic init -t async`) | URL settings'dan olinadi, `NullPool` |
| Settings | pydantic-settings v2 | `SettingsConfigDict`, nested `__` delimiter, `@lru_cache` factory |
| JWT | **PyJWT** | `python-jose` RAD ETILDI: CVE-2024-33663/33664, qarovsiz |
| Parol hash | **`pwdlib[argon2]`** (Argon2id) | `passlib` RAD ETILDI: 2020'dan yangilanmagan, bcrypt≥4.1 bilan sinadi |
| Task queue | Taskiq: `RedisStreamBroker` + `RedisAsyncResultBackend` + `TaskiqScheduler` | ack'li broker; `taskiq_fastapi.init(broker, "app.main:app")`; task ichida `TaskiqDepends` |
| Rate limit | slowapi (Redis storage, in-memory fallback) | `SlowAPIASGIMiddleware`; endpoint'da `request: Request` majburiy; Traefik ortida X-Forwarded-For'li key func |
| Cache | redis-py (async) dependency sifatida | broker/result/cache alohida Redis DB'lar (/0 /1 /2) |
| Logging | structlog | dev: ConsoleRenderer, prod: JSONRenderer; `merge_contextvars` + request-id middleware; har request boshida `clear_contextvars()` |
| Pagination | fastapi-pagination | `Page[Schema]` + sqlalchemy ext `paginate(db, stmt)`; doim `order_by`; `add_pagination(app)` router'lardan keyin |
| Monitoring | prometheus-fastapi-instrumentator | `/metrics` schema'dan tashqarida, Traefik orqali chiqarilmaydi |
| Errors | sentry-sdk | DSN bo'sh bo'lsa o'chiq; `init()` app yaratilishidan OLDIN; `send_default_pii=False` |
| Server | uvicorn (prod'da bir necha replica, har biri 1 worker) | Prometheus multiproc muammosidan qochish uchun replica-per-process modeli |
| Test | pytest + pytest-asyncio + httpx (`ASGITransport`) | transaction-rollback test session |
| Tooling | uv, ruff, mypy, Makefile | ruff PostToolUse hook bilan avtomatik |
| Pre-commit | pre-commit (ruff check + format, mypy) | CI'gacha lokal xato ushlash |
| CORS | `CORSMiddleware` | origin'lar settings'dan (`BACKEND_CORS_ORIGINS`) |
| Seed | `scripts/seed.py` (`make seed`) | `.env`'dagi `FIRST_SUPERUSER_EMAIL/PASSWORD`'dan birinchi superuser |

## 3. Struktura — domen-birinchi (Netflix Dispatch / Django apps uslubi)

Har domen o'z papkasida to'liq: `router → service → repository → models` qatlamlari domen ichida saqlanadi. Yangi domen qo'shish = bitta papka; domen o'chirish = bitta papka; microservice'ga ajratish oson.

```
FastAPI-Template/
├── app/
│   ├── main.py                  # app factory: lifespan, middleware, router'lar, instrumentator
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings), get_settings() @lru_cache
│   │   ├── security.py          # JWT encode/decode (PyJWT), PasswordHash (pwdlib)
│   │   ├── logging.py           # structlog konfiguratsiyasi (env'ga qarab renderer)
│   │   ├── exceptions.py        # AppError ierarxiyasi + exception handler'lar
│   │   └── rate_limit.py        # slowapi Limiter (Redis storage, XFF-aware key)
│   ├── db/
│   │   ├── base.py              # Base(AsyncAttrs, DeclarativeBase) + BaseModel mixin
│   │   │                        #   (UUID pk, created_at, updated_at)
│   │   └── session.py           # create_async_engine, async_sessionmaker, get_db
│   ├── common/
│   │   ├── schemas.py           # umumiy Pydantic: Msg, ErrorResponse va h.k.
│   │   └── repository.py        # BaseRepository[T]: get/create/update/delete
│   ├── middleware.py            # request-id bind (structlog contextvars)
│   ├── auth/                    # domen: autentifikatsiya
│   │   ├── router.py            # POST /register /login /refresh
│   │   ├── service.py           # AuthService: token yaratish/tekshirish, parol
│   │   ├── schemas.py           # TokenPair, LoginRequest, RegisterRequest
│   │   └── deps.py              # get_current_user (OAuth2PasswordBearer)
│   ├── users/                   # domen: foydalanuvchilar (namuna domen)
│   │   ├── models.py            # User (SQLAlchemy)
│   │   ├── schemas.py           # UserRead, UserUpdate
│   │   ├── repository.py        # UserRepository(BaseRepository[User])
│   │   ├── service.py           # UserService
│   │   ├── router.py            # GET /me, PATCH /me, GET / (paginated, namuna)
│   │   └── tasks.py             # welcome_email task (Taskiq namunasi)
│   ├── health/
│   │   └── router.py            # GET /health (DB + Redis ping), rate-limit exempt
│   └── tasks/
│       ├── broker.py            # RedisStreamBroker + result backend + taskiq_fastapi.init
│       └── scheduler.py         # TaskiqScheduler + LabelScheduleSource
├── migrations/                  # Alembic async: env.py settings'dan URL oladi
├── scripts/
│   └── seed.py                  # birinchi superuser (.env: FIRST_SUPERUSER_*)
├── tests/
│   ├── conftest.py              # test engine, rollback session, AsyncClient, user factory
│   ├── test_auth.py             # register/login/refresh/me to'liq oqim
│   └── test_users.py            # CRUD + pagination
├── docs/                        # 🇺🇿 qo'llanmalar (8-bo'limga qarang)
├── deployment/
│   ├── Dockerfile               # multi-stage: uv bilan build → slim runtime, non-root user
│   ├── docker-compose.yml       # prod stack (9-bo'lim)
│   └── grafana/                 # datasource + FastAPI dashboard provisioning
├── .github/workflows/
│   ├── ci.yml                   # PR: ruff, mypy, pytest (pg+redis services)
│   └── cd.yml                   # main: build → GHCR → SSH deploy → health check
├── docker-compose.dev.yml       # dev: postgres + redis
├── .pre-commit-config.yaml      # ruff check/format + mypy
├── Makefile                     # dev, migrate, makemigration, seed, test, lint, worker, scheduler
├── example.env
├── pyproject.toml
├── .gitignore, .dockerignore
└── README.md                    # 🇬🇧
```

**API versiyalash:** har domen router'i `main.py`'da `app.include_router(users.router, prefix="/api/v1/users", tags=["users"])` tarzida ulanadi — versiya prefix'i markazda, domen router'lari versiyadan bexabar qoladi.

**CORS:** `main.py`'da `CORSMiddleware`, ruxsat etilgan origin'lar `Settings.backend_cors_origins` (env: `BACKEND_CORS_ORIGINS`, vergul bilan ajratilgan ro'yxat) dan olinadi — bo'sh bo'lsa middleware qo'shilmaydi.

## 4. Auth oqimi (namuna domen)

1. `POST /api/v1/auth/register` — email+parol, Argon2id hash, user yaratiladi, welcome task navbatga qo'yiladi.
2. `POST /api/v1/auth/login` — access (qisqa TTL, 15 min) + refresh (7 kun) JWT juftligi. `sub`=user id, `exp` majburiy, decode'da `algorithms=["HS256"]` qat'iy pin.
3. `POST /api/v1/auth/refresh` — refresh token bilan yangi juftlik. Refresh tokenlar `token_type="refresh"` claim bilan farqlanadi.
4. `GET /api/v1/users/me` — `get_current_user` dependency orqali.

Xato holatlari: `jwt.ExpiredSignatureError`/`jwt.InvalidTokenError` → 401; band email → 409; noto'g'ri parol → 401 (bir xil xabar — user enumeration'ga qarshi).

## 5. Request lifecycle

Traefik (TLS, redirect) → uvicorn → middleware (request-id bind, `clear_contextvars`) → slowapi → router (`Depends`: get_db, get_current_user) → service → repository → response. Har log yozuvida `request_id`.

## 6. Taskiq

- `broker.py`: `RedisStreamBroker(url).with_result_backend(RedisAsyncResultBackend(result_ex_time=3600))`; `taskiq_fastapi.init(broker, "app.main:app")` — dotted path (circular import'dan qochish).
- `main.py` lifespan'da: `if not broker.is_worker_process: await broker.startup()` (aks holda worker cheksiz rekursiya).
- Ishga tushirish: `taskiq worker app.tasks.broker:broker` va `taskiq scheduler app.tasks.scheduler:scheduler` — alohida container'lar.
- Task ichida DB: `session: AsyncSession = TaskiqDepends(get_db)`.

## 7. Xatolarni boshqarish

- `core/exceptions.py`: `AppError` bazasi → `NotFoundError`, `ConflictError`, `PermissionDeniedError` va h.k.; har biri status_code + code slug'ga ega.
- Global handler'lar: `AppError` → strukturali JSON (`{"detail", "code"}`); kutilmagan xato → 500 + structlog `exception` + Sentry.
- Service qatlami HTTP'ni bilmaydi — domain exception tashlaydi, handler HTTP'ga o'giradi.

## 8. O'zbekcha qo'llanmalar — `docs/`

Har biri "Django'da bunday edi → FastAPI'da bunday" taqqoslash bilan:

1. `01-structure.md` — Django apps vs domen papkalari; qatlamlar nima uchun.
2. `02-config.md` — `settings.py` vs pydantic-settings; env boshqaruvi.
3. `03-database.md` — Django ORM vs SQLAlchemy 2.0 (query taqqoslash jadvali) ; Alembic vs migrations.
4. `04-auth.md` — `contrib.auth` vs qo'lda JWT; nega PyJWT/pwdlib.
5. `05-background-tasks.md` — Celery vs Taskiq; broker/worker/scheduler.
6. `06-observability.md` — structlog, Sentry, Prometheus/Grafana.
7. `07-deployment.md` — Traefik v3, compose, Dockerfile anatomiyasi.
8. `08-cicd.md` — GitHub Actions pipeline'lari, secrets.

## 9. Deployment

**Dev (`docker-compose.dev.yml`):** postgres:17 + redis:8, port'lar ochiq; API lokal `make dev` (`uvicorn app.main:app --reload`).

**Prod (`deployment/docker-compose.yml`):**
- `traefik` (v3.7): docker provider, `exposedbydefault=false`, entrypoint-level HTTP→HTTPS redirect, ACME httpchallenge, `acme.json` volume (chmod 600), `--providers.docker.network` aniq ko'rsatiladi.
- `api`: template image, uvicorn; Traefik label'lari (Host rule, websecure, certresolver); replicas oshirilishi mumkin.
- `worker`, `scheduler`: shu image, faqat command boshqa.
- `postgres`, `redis`: internal network, tashqariga chiqmaydi; postgres volume + healthcheck.
- `prometheus`: api'ning `/metrics`'ini ichki tarmoqdan scrape qiladi; `grafana`: provisioned datasource + dashboard, alohida subdomain'da Traefik orqali.
- Ikki network: `web` (traefik↔api/grafana) va `internal` (api↔db/redis/prometheus).

**Dockerfile:** stage 1 — `uv sync --frozen --no-dev`; stage 2 — slim runtime, faqat venv + app kodi, non-root user, `HEALTHCHECK`.

## 10. CI/CD (GitHub Actions)

**ci.yml** (PR + main push): checkout → `uv sync` → `ruff check` + `ruff format --check` → `mypy app` → `pytest` (services: postgres, redis; env test qiymatlari bilan).

**cd.yml** (main push, CI muvaffaqiyatidan keyin): buildx build → GHCR push (`latest` + sha tag) → `appleboy/ssh-action` bilan VPS'da `docker compose pull && docker compose up -d` → `/health` curl tekshiruv. Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

## 11. Testlar

- `conftest.py`: alohida test DB (`TEST_DATABASE_URL`), har test funksiya uchun transaction-rollback session; `httpx.AsyncClient(transport=ASGITransport(app))`; `get_db` dependency override; `user_factory` oddiy funksiya (fixture zanjiri emas).
- Qamrov: auth to'liq oqimi (register→login→me→refresh, xato holatlari bilan), users CRUD + pagination, health.
- `pytest-asyncio` `asyncio_mode = "auto"`.

## 12. Qamrovdan tashqarida (YAGNI)

- Email yuborish integratsiyasi (task faqat log yozadi — namuna sifatida).
- OAuth (Google/GitHub) login.
- Kubernetes manifest'lari (docker-compose VPS deploy yetarli).
- Multi-tenancy, i18n.
- Frontend/admin panel.

## 13. Muvaffaqiyat mezonlari

1. `make dev` bilan template birinchi urinishda ishga tushadi; `/docs` (Swagger) ochiladi.
2. `make test` — barcha testlar yashil; `make lint` toza.
3. `docker compose -f deployment/docker-compose.yml up` to'liq prod stack'ni ko'taradi.
4. CI workflow yashil; CD (secrets berilganda) VPS'ga deploy qiladi.
5. `docs/` dagi 8 qo'llanma Django'chi dasturchiga har qatlamni tushuntiradi.
