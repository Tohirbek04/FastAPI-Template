# 05 — Background tasks: Celery'dan Taskiq'qa

## Nega Celery emas?

Celery sync-dunyoda tug'ilgan: async FastAPI bilan ishlatishda event loop
atrofida aylanib o'tishlar kerak. **Taskiq** — async-native: task'lar
`async def`, worker asyncio ustida, hatto FastAPI `Depends` ham task ichida
ishlaydi.

## Taqqoslash jadvali

| Celery (Django'da) | Taskiq (bu template) |
|---|---|
| `@shared_task` | `@broker.task` |
| `send_email.delay(x)` | `await send_email.kiq(x)` |
| `apply_async(countdown=60)` | `.kicker().with_labels(delay=60).kiq(x)` |
| `celery -A conf worker` | `make worker` (`taskiq worker app.tasks.broker:broker`) |
| celery beat + `CELERY_BEAT_SCHEDULE` | `make scheduler` + `@broker.task(schedule=[{"cron": "0 3 * * *", "schedule_id": "daily"}])` |
| `CELERY_BROKER_URL` | `Settings.taskiq_broker_url` (redis db /1) |
| result backend | `RedisAsyncResultBackend` (db /2, TTL 1 soat) |
| `CELERY_TASK_ALWAYS_EAGER = True` (testda) | `InMemoryBroker` (`ENV=test`da avtomatik) |

## Arxitektura (app/tasks/broker.py)

```python
broker = RedisStreamBroker(url=...).with_result_backend(
    RedisAsyncResultBackend(redis_url=..., result_ex_time=3600)
)
taskiq_fastapi.init(broker, "app.main:app")
```

- **RedisStreamBroker** (oddiy `ListQueueBroker` emas) — Redis Streams +
  acknowledgement: worker task o'rtasida o'lib qolsa, task boshqa worker'ga
  qayta beriladi. Celery'dagi `acks_late`ning ekvivalenti, lekin default.
- **`taskiq_fastapi.init(broker, "app.main:app")`** — string yo'l (import
  emas!) circular import'ning oldini oladi va task'larga FastAPI dependency
  tizimini ulaydi.
- Redis DB taqsimoti: `/0` cache+rate-limit, `/1` broker, `/2` natijalar —
  `FLUSHDB` bir tizimni tozalasa, boshqasiga tegmaydi.

## Task yozish (app/users/tasks.py — namuna)

```python
@broker.task
async def send_welcome_email(email: str) -> None:
    logger.info("welcome_email_sent", email=email)
```

Task ichida DB kerak bo'lsa — `TaskiqDepends` (FastAPI `Depends`ning
task-dunyodagi ekvivalenti):

```python
from taskiq import TaskiqDepends

@broker.task
async def cleanup_inactive(session: AsyncSession = TaskiqDepends(get_db)) -> None:
    ...
```

Chaqirish (`app/auth/service.py`dagi real misol):

```python
await send_welcome_email.kiq(user.email)   # navbatga qo'yadi, kutmaydi
```

## Lifespan tuzog'i (app/main.py)

```python
if not broker.is_worker_process:
    await broker.startup()
```

`taskiq worker` jarayoni ham `app.main:app`ni import qiladi (dependency'lar
uchun). Agar guard bo'lmasa, worker o'zini qayta-qayta startup qilib cheksiz
rekursiyaga tushadi. Bu — Taskiq'ning eng mashhur tuzog'i, guard doim tursin.

## Ishga tushirish

```bash
make worker      # navbatdagi task'larni bajaradi
make scheduler   # cron label'li task'larni vaqtida otadi
```

Prod'da (deployment/docker-compose.yml) `api`, `worker`, `scheduler` — bitta
image'dan uchta alohida container, faqat `command` farq qiladi. Yuk oshsa
`docker compose up -d --scale worker=3` — task'lar avtomatik taqsimlanadi.

## Testlash (tests/test_tasks.py)

`ENV=test`da broker `InMemoryBroker(await_inplace=True)` bo'ladi: `.kiq()`
task'ni darhol shu yerda bajaradi — Redis ham, worker ham kerak emas.
`structlog.testing.capture_logs()` bilan task ichidagi log tekshiriladi.
