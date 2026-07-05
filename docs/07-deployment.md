# 07 — Deployment: Traefik v3 + Docker Compose

## Arxitektura

```
Internet
   │ :80 (→ :443 redirect), :443 TLS
┌──▼──────────────────────────────────────────── web network ──┐
│  Traefik v3          Grafana (grafana.<DOMAIN>)              │
│     │ Host(`<DOMAIN>`)                                       │
└─────┼─────────────────────────────────────────────────────────┘
┌─────▼──────────────────────────────────── internal network ──┐
│  api (uvicorn :8000)   worker   scheduler                    │
│      │           │        │        │                         │
│  Postgres ◄──────┴────────┴─► Redis     Prometheus → api:8000/metrics │
└───────────────────────────────────────────────────────────────┘
```

Ikki tarmoq nima uchun: `web`da faqat internetga ko'rinishi kerak bo'lganlar
(Traefik, api, grafana). Postgres/Redis/Prometheus `internal`da — ularga
internetdan yo'l **yo'q**, port publish qilinmagan.

## Django template bilan farq

| Django template (sizdagi) | Bu template |
|---|---|
| gunicorn (WSGI, sync worker'lar) | uvicorn (ASGI, async) |
| Nginx (qo'lda config + certbot) | Traefik v3 (label'lardan avtokonfiguratsiya + avto Let's Encrypt) |
| celery + celery-beat container'lari | taskiq worker + scheduler container'lari |

## Traefik v3 qanday ishlaydi

Traefik docker socket'ni kuzatadi va **label'lardan** routing yasaydi —
alohida nginx.conf yo'q. `deployment/docker-compose.yml`dagi api label'lari:

```yaml
- "traefik.enable=true"                                  # exposedbydefault=false, shuning uchun explicit
- "traefik.http.routers.api.rule=Host(`${DOMAIN}`)"      # qaysi domen shu servisga
- "traefik.http.routers.api.entrypoints=websecure"       # faqat :443
- "traefik.http.routers.api.tls.certresolver=le"         # Let's Encrypt
- "traefik.http.services.api.loadbalancer.server.port=8000"
```

Muhim nuqtalar:

- **HTTP→HTTPS** redirect entrypoint darajasida global (traefik command'ida) —
  har servisga alohida middleware kerak emas.
- **Let's Encrypt**: birinchi so'rovda Traefik ACME http-challenge orqali
  sertifikat oladi, `letsencrypt` volume'dagi `acme.json`da saqlaydi va o'zi
  yangilab boradi. Certbot cron'lari — tarixda qoldi.
- `--providers.docker.network=web` — Traefik container IP'sini to'g'ri
  tarmoqdan olishi uchun (api ikkala tarmoqda turadi).

## Dockerfile anatomiyasi (deployment/Dockerfile)

Ikki bosqich:

1. **builder** (uv image): avval faqat `pyproject.toml + uv.lock` ko'chiriladi
   va `uv sync --frozen --no-dev` — dependency layer keshda qoladi, kod
   o'zgarganda qayta o'rnatilmaydi (build 10x tez).
2. **runtime** (python slim): faqat tayyor `.venv` + kod ko'chiriladi.
   Natija: kichik image, ichida build asboblari yo'q.

Xavfsizlik: `USER app` (non-root) — container ichiga kirgan hujumchi root
bo'lmaydi. `HEALTHCHECK` `/api/v1/health`ni tekshiradi (u DB+Redis'ga chin
ping qiladi) — docker "sog'lom emas" container'ni ko'rsatib turadi.

Migratsiyalar api startida (`alembic upgrade head && uvicorn ...`) — bitta
api replica bilan xavfsiz. Replica ko'paysa, migratsiyani alohida one-shot
service'ga chiqaring (`deployment/README.md`da eslatilgan).

## VPS'ga birinchi deploy (checklist)

1. Serverga Docker + compose plugin o'rnating
2. `mkdir -p /opt/fastapi-template && cd /opt/fastapi-template`
3. `deployment/` papkasini serverga ko'chiring (scp/rsync yoki git clone)
4. `deployment/.env` yarating (`example.env`dan nusxa) va to'ldiring:
   - `ENV=prod`, `DEBUG=false`
   - kuchli `SECRET_KEY` (`openssl rand -base64 48`), `POSTGRES_PASSWORD`,
     `GRAFANA_ADMIN_PASSWORD` (`openssl rand -base64 32`)
   - `DOMAIN=api.sizningdomen.uz`, `ACME_EMAIL=...`
   - `DATABASE_URL=postgresql+asyncpg://app:<POSTGRES_PASSWORD>@postgres:5432/app`
     (host endi `postgres` — container nomi, `localhost` emas!)
   - `REDIS_URL=redis://redis:6379/0`
   - `DOCKER_IMAGE=ghcr.io/<owner>/<repo>:latest`
5. DNS: `api.domen.uz` va `grafana.api.domen.uz` A-yozuvlari server IP'ga
6. `cd deployment && docker compose up -d`
7. Tekshirish: `curl https://api.domen.uz/api/v1/health` → `{"detail":"ok"}`
8. Superuser: `docker compose exec api python scripts/seed.py`

Keyingi deploy'lar avtomatik — CI/CD (08-qo'llanma).

## Proxy headers eslatmasi

api uvicorn'i `--proxy-headers --forwarded-allow-ips='*'` bilan ishlaydi —
`request.client.host` Traefik yozgan haqiqiy klient IP bo'ladi (rate limiting
shunga tayanadi). Bu xavfsiz, chunki api'ga faqat Traefik yeta oladi; **8000
portni hech qachon to'g'ridan-to'g'ri publish qilmang.**
