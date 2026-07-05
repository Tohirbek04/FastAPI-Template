import taskiq_fastapi
from taskiq import AsyncBroker, InMemoryBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.core.config import get_settings

_settings = get_settings()

broker: AsyncBroker
if _settings.env == "test":
    # await_inplace=True makes kiq() run the task immediately in place;
    # otherwise it is scheduled as a background asyncio task and may finish
    # after a test's capture_logs() block has already exited (race).
    broker = InMemoryBroker(await_inplace=True)
else:
    # RedisStreamBroker acknowledges messages: tasks survive worker crashes.
    broker = RedisStreamBroker(url=_settings.taskiq_broker_url).with_result_backend(
        RedisAsyncResultBackend(redis_url=_settings.taskiq_result_url, result_ex_time=3600)
    )

# The dotted path avoids a circular import with app.main.
taskiq_fastapi.init(broker, "app.main:app")
