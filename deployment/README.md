# Deployment

## First-time VPS setup

1. Install Docker + the compose plugin.
2. `mkdir -p /opt/fastapi-template && cd /opt/fastapi-template`
3. Copy this `deployment/` directory to the server.
4. `cp example.env deployment/.env` and edit:
   - `ENV=prod`, `DEBUG=false`
   - a real `SECRET_KEY` (32+ random chars), `POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`
   - `DOMAIN`, `ACME_EMAIL`
   - `DATABASE_URL=postgresql+asyncpg://app:<POSTGRES_PASSWORD>@postgres:5432/app`
   - `REDIS_URL=redis://redis:6379/0`
   - `DOCKER_IMAGE=ghcr.io/<owner>/<repo>:latest`
5. `cd deployment && docker compose up -d`

Traefik obtains Let's Encrypt certificates automatically (HTTP-01 challenge);
`acme.json` persists in the `letsencrypt` volume.

## Notes

- `/metrics` is NOT routed through Traefik — Prometheus scrapes it on the
  internal network only.
- Grafana lives at `https://grafana.<DOMAIN>` (provisioned Prometheus
  datasource; import a FastAPI dashboard, e.g. grafana.com ID 11713).
- Migrations run automatically before the api starts (`alembic upgrade head`).
  With more than one api replica, run migrations as a separate one-shot
  service instead to avoid concurrent migration races.
- The api container trusts proxy headers (`--proxy-headers
  --forwarded-allow-ips='*'`) — safe because it is only reachable through
  Traefik on the internal docker network. Do not publish port 8000 directly.
