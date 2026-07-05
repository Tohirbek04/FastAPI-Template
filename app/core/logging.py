import logging

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Dev: rangli console; prod: JSON (Grafana/Loki uchun)."""
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
        # Keshlash faqat prod'da: testlarda capture_logs() keshlangan
        # logger'larni almashtira olmaydi.
        cache_logger_on_first_use=settings.env == "prod",
    )
