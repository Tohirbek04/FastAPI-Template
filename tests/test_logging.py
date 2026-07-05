import structlog
from app.core.logging import configure_logging
from app.middleware import RequestContextMiddleware


def test_configure_logging_is_idempotent() -> None:
    configure_logging()
    configure_logging()
    structlog.get_logger().info("test_event", key="value")  # must not raise


async def test_middleware_binds_request_id() -> None:
    captured: dict[str, object] = {}

    async def inner_app(scope, receive, send) -> None:
        captured.update(structlog.contextvars.get_contextvars())

    middleware = RequestContextMiddleware(inner_app)
    scope = {
        "type": "http",
        "path": "/api/v1/health",
        "headers": [(b"x-request-id", b"req-123")],
    }

    async def receive():
        return {"type": "http.request"}

    async def send(message) -> None:
        return None

    await middleware(scope, receive, send)

    assert captured["request_id"] == "req-123"
    assert captured["path"] == "/api/v1/health"
