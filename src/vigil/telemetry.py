"""OpenTelemetry setup.

Every agent hop, model call, tool call and policy decision becomes a span. That
is what makes the reasoning chain auditable after the fact — the "glass box"
view in the UI is just a rendering of these spans, and the same spans land in
Cloud Trace once deployed.

Locally they go to Jaeger (docker-compose) so none of this needs a cloud project.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False


def setup_telemetry(service_name: str) -> None:
    global _configured
    if _configured:
        return

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "deployment.environment": os.environ.get("VIGIL_ENV", "local"),
            }
        )
    )
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
        )
    trace.set_tracer_provider(provider)
    _configured = True


def tracer(name: str = "vigil"):
    return trace.get_tracer(name)


def log(name: str = "vigil"):
    return structlog.get_logger(name)


@contextmanager
def span(name: str, **attributes):
    """Span helper that also stamps the attributes onto the structlog context, so
    a log line and its trace entry can always be joined on run_id/step_id."""
    with tracer().start_as_current_span(name) as s:
        for key, value in attributes.items():
            if value is not None:
                s.set_attribute(key, value)
        with structlog.contextvars.bound_contextvars(**attributes):
            yield s


def current_trace_id() -> str | None:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else None
