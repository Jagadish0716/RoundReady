from fastapi import FastAPI
from roundready_common.correlation import CorrelationIdMiddleware
from roundready_common.http import install_exception_handlers
from roundready_common.logging import RequestLoggingMiddleware, configure_logging
from roundready_common.metrics import MetricsMiddleware, metrics_endpoint
from roundready_common.telemetry import configure_telemetry

from app.api.health import router as health_router
from app.api.routes import router as notification_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    app = FastAPI(title="RoundReady Notification Service", version="0.1.0")
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    install_exception_handlers(app)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
    app.include_router(health_router)
    app.include_router(notification_router)
    configure_telemetry(app, settings.service_name, settings.telemetry_enabled)
    return app


app = create_app()
