from __future__ import annotations

import contextvars
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from .config import settings


EXTRA_FIELDS = ("request_id", "job_id", "dag_id")

_request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_job_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)
_dag_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("dag_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting logic
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple setter
        record.request_id = _request_id_ctx.get()
        record.job_id = _job_id_ctx.get()
        record.dag_id = _dag_id_ctx.get()
        return True


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    handler.setLevel(level)
    root.addHandler(handler)


def bind_request_context(request_id: Optional[str] = None) -> contextvars.Token:
    return _request_id_ctx.set(request_id)


def reset_request_context(token: contextvars.Token) -> None:
    _request_id_ctx.reset(token)


@contextmanager
def log_context(*, request_id: Optional[str] = None, job_id: Optional[str] = None, dag_id: Optional[str] = None) -> Iterator[None]:
    tokens: list[tuple[contextvars.ContextVar, contextvars.Token]] = []
    if request_id is not None:
        tokens.append((_request_id_ctx, _request_id_ctx.set(request_id)))
    if job_id is not None:
        tokens.append((_job_id_ctx, _job_id_ctx.set(job_id)))
    if dag_id is not None:
        tokens.append((_dag_id_ctx, _dag_id_ctx.set(dag_id)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):  # pragma: no cover - trivial
            var.reset(token)


__all__ = [
    "setup_logging",
    "log_context",
    "bind_request_context",
    "reset_request_context",
]
