"""Structured logging configuration using structlog.

All logs are emitted as JSON in production and pretty-printed in development.
A correlation ID (request-id) is attached to every log line within a request scope.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    """Bind a request ID to the current async context."""
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    """Return the request ID for the current async context, if any."""
    return _request_id_ctx.get()


def _add_request_id(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Structlog processor that injects the current request ID."""
    rid = _request_id_ctx.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structlog and the stdlib root logger.

    Args:
        level: Minimum log level (e.g. "INFO", "DEBUG").
        json_logs: If True, emit JSON; otherwise pretty console output.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a logger bound to the given name."""
    return structlog.get_logger(name)
