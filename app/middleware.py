import uuid

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestContextMiddleware:
    """Clear structlog context per request and bind request_id/path,
    so every log line emitted while handling the request carries them.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        structlog.contextvars.clear_contextvars()
        headers = dict(scope["headers"])
        request_id = headers.get(b"x-request-id", uuid.uuid4().hex.encode()).decode()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=scope["path"])
        await self.app(scope, receive, send)
