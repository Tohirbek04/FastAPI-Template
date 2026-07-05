import logging

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Pretty console output in dev, JSON in prod (for log aggregators)."""
    settings = get_settings()
    shared: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.env == "prod"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        # Cache loggers only in prod: cached loggers ignore the temporary
        # configuration that structlog's capture_logs() installs in tests.
        cache_logger_on_first_use=settings.env == "prod",
    )
