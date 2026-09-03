from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from roundready_common.correlation import CorrelationIdMiddleware
from roundready_common.http import install_exception_handlers
from roundready_common.logging import RequestLoggingMiddleware, configure_logging
from roundready_common.metrics import MetricsMiddleware, metrics_endpoint
from roundready_common.telemetry import configure_telemetry

from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    app = FastAPI(title="RoundReady API Gateway", version="0.1.0")

    def add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment == "production" and settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.middleware("http")
    async def security_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        try:
            request_size = int(content_length) if content_length is not None else 0
        except ValueError:
            return add_security_headers(
                JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
            )
        if request_size < 0:
            return add_security_headers(
                JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
            )
        if request_size > settings.max_request_body_bytes:
            return add_security_headers(
                JSONResponse(status_code=413, content={"detail": "Request body is too large"})
            )
        response = await call_next(request)
        return add_security_headers(response)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
        )
    install_exception_handlers(app)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
    app.include_router(health_router)
    app.include_router(api_router)
    configure_telemetry(app, settings.service_name, settings.telemetry_enabled)
    return app


app = create_app()
