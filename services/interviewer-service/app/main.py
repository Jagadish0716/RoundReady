from fastapi import FastAPI
from roundready_common.correlation import CorrelationIdMiddleware
from roundready_common.http import install_exception_handlers
from roundready_common.logging import configure_logging
from roundready_common.telemetry import configure_telemetry

from app.api.health import router as health_router
from app.api.routes import router as interviewer_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="RoundReady Interviewer Service", version="0.1.0")
    app.add_middleware(CorrelationIdMiddleware)
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(interviewer_router)
    configure_telemetry(app, settings.service_name, settings.telemetry_enabled)
    return app


app = create_app()
