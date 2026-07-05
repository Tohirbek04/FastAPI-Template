import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.core.config import get_settings

_settings = get_settings()

broker: AsyncBroker
if _settings.env == "test":
    # await_inplace=True — kiq() task'ni darhol, o'sha yerda bajaradi;
    # aks holda asyncio.create_task fon rejimida ishga tushib, test
    # capture_logs() blokidan chiqqandan keyin bajarilishi mumkin (race).
    broker = InMemoryBroker(await_inplace=True)
else:
    # RedisStreamBroker — ack bilan: worker o'lsa ham task yo'qolmaydi
    broker = RedisStreamBroker(url=_settings.taskiq_broker_url).with_result_backend(
        RedisAsyncResultBackend(redis_url=_settings.taskiq_result_url, result_ex_time=3600)
    )

# Dotted path — circular import'ning oldini oladi
taskiq_fastapi.init(broker, "app.main:app")
