import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_telemetry(
    app: FastAPI, service_name: str, enabled: bool, endpoint: str | None = None
) -> None:
    if not enabled:
        return
    try:
        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
        exporter_endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if exporter_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=exporter_endpoint))
            )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()

        async def shutdown_telemetry() -> None:
            provider.shutdown()

        app.router.on_shutdown.append(shutdown_telemetry)
    except Exception as exc:
        logging.getLogger(__name__).warning("telemetry_setup_failed", exc_info=exc)
