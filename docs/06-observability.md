# 06 — Observability: log, xato va metrikalar

## Structured logging (structlog)

Django'da `LOGGING` dict + oddiy matnli qatorlar. Bu yerda har log yozuvi —
**strukturali event**:

```python
logger.info("welcome_email_sent", email=email)
```

Dev'da (`ENV=dev`) — rangli, o'qish oson console. Prod'da (`ENV=prod`) —
JSON: `{"event": "welcome_email_sent", "email": "...", "request_id": "...",
"timestamp": "..."}`. JSON'ni Loki/ELK indekslaydi, "shu request'da nima
bo'lgan?" degan savolga bitta filter bilan javob topiladi.

Konfiguratsiya `app/core/logging.py`da: `configure_logging()` bitta funksiya,
`main.py` startda chaqiradi.

## Request-ID correlation (app/middleware.py)

`RequestContextMiddleware` har so'rovda:

1. `structlog.contextvars.clear_contextvars()` — avvalgi so'rov konteksti
   qolib ketmasin (async'da bitta worker minglab so'rovlarni aralash bajaradi)
2. `X-Request-ID` header'ini o'qiydi (Traefik/klient bergan bo'lsa) yoki yangi
   uuid yaratadi
3. `bind_contextvars(request_id=..., path=...)` — shundan keyin **shu so'rov
   davomida yozilgan HAR log** avtomatik `request_id` bilan chiqadi

Django'da buning uchun `django-log-request-id` kabi paket kerak edi; bu yerda
20 qator ASGI middleware.

## Sentry (ixtiyoriy)

`.env`da `SENTRY_DSN` to'ldirilsa — yoqiladi, bo'sh bo'lsa umuman chaqirilmaydi
(`app/main.py`):

```python
sentry_sdk.init(dsn=..., environment=settings.env,
                traces_sample_rate=0.1, send_default_pii=False)
```

- `traces_sample_rate=0.1` — so'rovlarning 10%ida performance trace (100%
  prod'da qimmat)
- `send_default_pii=False` — foydalanuvchi IP/header'lari yuborilmaydi

Handler'da tutilmagan har qanday exception avtomatik Sentry'ga tushadi.

## Prometheus + Grafana

`prometheus-fastapi-instrumentator` `/metrics` endpoint'ini ochadi
(`app/main.py`): so'rovlar soni, latency histogrammalari, status kodlar —
handler bo'yicha kesimda.

Xavfsizlik: `/metrics` **Traefik orqali internetga chiqarilmaydi** — prod
compose'da Prometheus uni faqat ichki docker tarmog'idan o'qiydi
(`deployment/prometheus/prometheus.yml`, target `api:8000`).

Grafana `grafana.<DOMAIN>`da, Prometheus datasource avtomatik provision
qilinadi (`deployment/grafana/provisioning/`). Tayyor dashboard: grafana.com
ID **11713** (FastAPI) import qiling.

## Django bilan taqqoslama

| Django | Bu template |
|---|---|
| `LOGGING` dict (100+ qator) | `configure_logging()` (~25 qator) |
| matnli log | strukturali event (prod'da JSON) |
| django-log-request-id | RequestContextMiddleware |
| django-prometheus | prometheus-fastapi-instrumentator |
| sentry-sdk (DjangoIntegration) | sentry-sdk (FastAPI avtomatik aniqlanadi) |

## Kundalik foydalanish

- Kod yozayotganda: `logger = structlog.get_logger()` moduling boshida,
  keyin `logger.info("event_nomi", kalit=qiymat)`. Event nomlari —
  `snake_case`, o'tgan zamon fe'li (`user_created`, `payment_failed`).
- Exception log qilish: `logger.exception("payment_failed", order_id=...)` —
  traceback avtomatik qo'shiladi (`format_exc_info` processor).
- Testda log tekshirish: `with structlog.testing.capture_logs() as logs: ...`
  (`tests/test_tasks.py`da misol).
