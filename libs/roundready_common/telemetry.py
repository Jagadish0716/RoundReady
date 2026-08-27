from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider


def configure_telemetry(app: FastAPI, service_name: str, enabled: bool) -> None:
    if not enabled:
        return
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
