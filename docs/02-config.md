# 02 — Konfiguratsiya: settings.py'dan pydantic-settings'ga

## Django'da bunday edi

```python
# conf/settings/base.py
DEBUG = env.bool("DEBUG", False)
DATABASES = {"default": env.db("DATABASE_URL")}
SECRET_KEY = env.str("SECRET_KEY")
```

Sozlamalar modul darajasidagi o'zgaruvchilar, `django-environ` env o'qiydi,
`DJANGO_SETTINGS_MODULE` qaysi fayl ishlashini tanlaydi.

## FastAPI template'da

Hammasi bitta tipli klass — `app/core/config.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    secret_key: str                      # default YO'Q — env'da bo'lishi SHART
    database_url: str
    redis_url: str = "redis://localhost:6380/0"
```

Afzalliklari:

- **Validatsiya startda.** `SECRET_KEY` berilmasa, ilova umuman ko'tarilmaydi —
  Django'dagi kabi runtime'da "None" bilan yashab yurmaydi.
- **Tiplar.** `debug: bool` — `"true"/"1"/"yes"` avtomatik bool bo'ladi;
  `backend_cors_origins: list[str]` — env'da JSON ro'yxat: `["http://..."]`.
- **Bitta klass, uch muhit.** `ENV=dev|test|prod` qiymati xatti-harakatni
  boshqaradi (log formati, rate-limit storage, broker turi) — Django'dagi
  `settings/dev.py`, `settings/prod.py` fayllar shajarasi kerak emas.

## `get_settings()` va nega `@lru_cache`

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Har chaqiruvda `.env` faylni qayta o'qimaslik uchun natija keshlanadi.
Testda boshqa qiymat kerak bo'lsa: `get_settings.cache_clear()`
(`tests/test_seed.py`da real misol bor).

## Env o'zgaruvchilar lug'ati (example.env)

| Kalit | Ma'nosi |
|---|---|
| `ENV` | `dev` / `test` / `prod` — muhit rejimi |
| `DEBUG` | `true`da log darajasi DEBUG, SQL echo yoqiladi |
| `SECRET_KEY` | JWT imzosi. 32+ tasodifiy belgi. **Hech qachon commit qilmang** |
| `ACCESS_TOKEN_TTL_MIN` | access token umri (default 15 daqiqa) |
| `REFRESH_TOKEN_TTL_DAYS` | refresh token umri (default 7 kun) |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:port/db` |
| `REDIS_URL` | cache/rate-limit bazasi (`/0`); taskiq broker `/1`, natijalar `/2` — `Settings.taskiq_broker_url` avtomatik hosil qiladi |
| `BACKEND_CORS_ORIGINS` | JSON ro'yxat; bo'sh `[]` — CORS middleware umuman qo'shilmaydi |
| `SENTRY_DSN` | bo'sh bo'lsa Sentry o'chiq |
| `FIRST_SUPERUSER_EMAIL/PASSWORD` | `make seed` uchun |
| `DOMAIN`, `ACME_EMAIL` | prod compose: Traefik host rule + Let's Encrypt |
| `POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `DOCKER_IMAGE` | faqat prod compose ishlatadi |

## Oqim

```
example.env  --cp-->  .env (gitignore'da!)  --pydantic-settings-->  Settings
```

Yangi sozlama qo'shish: (1) `Settings`ga maydon qo'shing, (2) `example.env`ga
hujjatlangan misol qator qo'shing. Ikkalasisiz PR ochmang — template shartnomasi
shu.

## Django bilan yakuniy taqqoslama

| Django | Bu template |
|---|---|
| `settings/base.py + dev.py + prod.py` | bitta `Settings` + `ENV` qiymati |
| `django-environ` | pydantic-settings (tip + validatsiya) |
| `DJANGO_SETTINGS_MODULE` | kerak emas |
| import paytida o'qiladi | `get_settings()` chaqirilganda (keshlangan) |
| `settings.SECRET_KEY` global | `Depends`/import orqali explicit |
