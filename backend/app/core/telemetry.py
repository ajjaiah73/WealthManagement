"""OpenTelemetry tracer provider setup. No exporter is configured yet — spans
are created but not shipped anywhere. Wire an OTLP exporter here once an
observability backend is available (see spec's Observability section)."""
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

_configured = False


def configure_telemetry(service_name: str = "superannuation-advisory-api") -> None:
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
