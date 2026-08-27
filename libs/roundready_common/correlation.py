from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp

CORRELATION_HEADER = "X-Correlation-ID"
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="unknown")


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, object],
        receive: Callable[[], Awaitable[dict[str, object]]],
        send: Callable[[dict[str, object]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)  # type: ignore[arg-type]
            return
        request = Request(scope)  # type: ignore[arg-type]
        correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid4())
        token: Token[str] = _correlation_id.set(correlation_id)

        async def send_with_header(message: dict[str, object]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))  # type: ignore[arg-type]
                headers.append((CORRELATION_HEADER.lower().encode(), correlation_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)  # type: ignore[arg-type]
        finally:
            _correlation_id.reset(token)
