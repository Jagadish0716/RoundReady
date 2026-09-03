import logging
import sys
from collections.abc import MutableMapping
from time import perf_counter
from typing import Any, cast

import structlog
from opentelemetry import trace
from starlette.types import ASGIApp, Receive, Scope, Send

from roundready_common.correlation import get_correlation_id

_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "signature",
    "token",
    "credential",
}


def redact_sensitive_data(value: Any, key: str | None = None) -> Any:
    if key is not None and any(part in key.lower() for part in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: redact_sensitive_data(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    return value


def add_correlation_id(
    _logger: Any, _method: str, event: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    event.setdefault("correlation_id", get_correlation_id())
    return cast(MutableMapping[str, Any], redact_sensitive_data(event))


def add_trace_context(
    _logger: Any, _method: str, event: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    span = trace.get_current_span()
    context = span.get_span_context()
    if context.is_valid:
        event.setdefault("trace_id", format(context.trace_id, "032x"))
        event.setdefault("span_id", format(context.span_id, "016x"))
    return event


def configure_logging(
    log_level: str, service_name: str = "unknown", environment: str = "unknown"
) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level.upper())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_correlation_id,
            add_trace_context,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service_name, environment=environment)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        if path in {"/health", "/ready"}:
            await self.app(scope, receive, send)
            return
        status_code = 500

        async def capture_status(message: Any) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        started = perf_counter()
        await self.app(scope, receive, capture_status)
        structlog.get_logger().info(
            "http_request",
            method=scope.get("method"),
            path=path,
            status_code=status_code,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
