# 08 — CI/CD: GitHub Actions pipeline'lari

## Umumiy oqim

```
PR ochildi ──► CI: ruff → mypy → pytest ──► yashil bo'lsa merge mumkin
                                │
main'ga push ──► CI (yana) ──► CD: image build → GHCR push → SSH deploy → health check
```

## CI (.github/workflows/ci.yml)

Har PR va main push'da ishlaydi. Qadamlar:

1. **Services**: runner yonida Postgres 17 + Redis 8 container'lari
   ko'tariladi — xuddi lokal `make db` kabi, lekin standart portlarda (5432).
   `TEST_DATABASE_URL` env orqali conftest'ga yetkaziladi — conftest avval
   env'ni o'qiydi, topilmasa lokal defaultga (5435) tushadi. Shu bitta env
   bilan lokal va CI bir xil kodda ishlaydi.
2. `uv sync --frozen` — lock fayldan aynan o'sha versiyalar (frozen: lock
   eskirgan bo'lsa xato — "menda ishlayapti-ku" muammosi yo'q).
3. `ruff check` + `ruff format --check` — stil; `mypy` — tiplar;
   `pytest -v` — to'liq suite.

Django'dagi odatiy CI'dan farqi: `pip install -r requirements.txt` o'rniga
lock-based `uv sync` (tezroq va deterministik).

## CD (.github/workflows/cd.yml)

**Trigger:** `workflow_run` — "CI nomli workflow main'da muvaffaqiyatli
tugadi". Ya'ni test yiqilsa, deploy umuman boshlanmaydi.

**build job:**
- `docker/build-push-action` `deployment/Dockerfile`ni build qilib GHCR'ga
  ikki teg bilan push qiladi: `:latest` va `:<commit-sha>` (rollback uchun —
  istalgan eski sha'ga qaytish mumkin)
- `GITHUB_TOKEN` bilan login — alohida registry token kerak emas
  (`permissions: packages: write`)
- `cache-from/to: type=gha` — dependency layer'lar Actions keshida, build
  odatda 1-2 daqiqa

**deploy job:**
- `appleboy/ssh-action` VPS'ga ulanib: `docker compose pull && up -d` —
  compose faqat o'zgargan image'ni qayta yaratadi, downtime sekundlar
- oxirida `curl -fsS https://<domain>/api/v1/health` — deploy'dan keyin API
  chindan tirikligini tasdiqlaydi; yiqilsa workflow qizil bo'ladi

**Xavfsizlik:** barcha action'lar to'liq commit SHA'ga pin qilingan
(`uses: appleboy/ssh-action@0ff42...  # v1.2.5`) — teg (`@v1`) hujum ostida
almashtirilishi mumkin, SHA — yo'q.

## Sozlash (yangi loyiha checklist'i)

1. GitHub'da repo yarating, template'ni push qiling
2. **Settings → Secrets and variables → Actions** ga qo'shing:

   | Secret | Qiymat |
   |---|---|
   | `VPS_HOST` | server IP yoki domen |
   | `VPS_USER` | ssh foydalanuvchi (masalan `deploy`) |
   | `VPS_SSH_KEY` | private key (pastga qarang) |
   | `API_DOMAIN` | `api.domen.uz` (health check uchun) |

3. Deploy kaliti yaratish (lokalda):
   ```bash
   ssh-keygen -t ed25519 -f deploy_key -C "gh-actions-deploy" -N ""
   ssh-copy-id -i deploy_key.pub deploy@SERVER   # public key serverga
   cat deploy_key                                 # private key → VPS_SSH_KEY secret
   rm deploy_key deploy_key.pub                   # lokalda saqlamang
   ```
4. Serverda GHCR'dan pull uchun (private repo bo'lsa):
   `docker login ghcr.io -u <username> -p <PAT with read:packages>`
5. `deployment/.env`dagi `DOCKER_IMAGE`ni o'z repo'ingizga moslang:
   `ghcr.io/<owner>/<repo>:latest`
6. main'ga push qiling — CI yashil bo'lgach CD o'zi deploy qiladi

## Kengaytirish g'oyalari

- **Staging muhit**: `develop` branch → alohida compose loyiha nomi bilan
  ikkinchi deploy job
- **Coverage gate**: pytest'ga `--cov=app --cov-fail-under=80`
- **Migratsiya xavfsizligi**: deploy skriptiga
  `docker compose run --rm api alembic upgrade head` ni alohida qadam qilib
  chiqarish (api restart'idan oldin)
