from time import perf_counter

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HTTP_REQUESTS = Counter(
    "roundready_http_requests_total",
    "HTTP requests handled by a service",
    ("method", "route", "status_class"),
)
HTTP_REQUEST_DURATION = Histogram(
    "roundready_http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
)
BROKER_EVENTS = Counter(
    "roundready_broker_events_total",
    "Broker event processing outcomes",
    ("operation", "result"),
)
OUTBOX_EVENTS = Counter(
    "roundready_outbox_events_total",
    "Outbox publishing outcomes",
    ("result",),
)
REDIS_OPERATIONS = Counter(
    "roundready_redis_operations_total",
    "Redis operation outcomes",
    ("operation", "result"),
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def metrics_endpoint(_request: Request) -> Response:
    return metrics_response()


def normalized_route(scope: Scope) -> str:
    route = scope.get("route")
    if route is not None and getattr(route, "path", None):
        return str(route.path)
    path = str(scope.get("path", ""))
    return "/unmatched" if not path else "/unmatched"


class MetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in {"/health", "/ready", "/metrics"}:
            await self.app(scope, receive, send)
            return
        status_code = 500

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        started = perf_counter()
        await self.app(scope, receive, capture_status)
        route = normalized_route(scope)
        method = str(scope.get("method", "UNKNOWN"))
        HTTP_REQUESTS.labels(method, route, f"{status_code // 100}xx").inc()
        HTTP_REQUEST_DURATION.labels(method, route).observe(perf_counter() - started)


def record_broker(operation: str, result: str) -> None:
    BROKER_EVENTS.labels(operation, result).inc()


def record_outbox(result: str) -> None:
    OUTBOX_EVENTS.labels(result).inc()


def record_redis(operation: str, result: str) -> None:
    REDIS_OPERATIONS.labels(operation, result).inc()
