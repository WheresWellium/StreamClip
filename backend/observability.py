"""Optional OpenTelemetry bootstrap (no-op when endpoint unset or SDK missing)."""

from __future__ import annotations

import structlog

from core.config import Settings

log = structlog.get_logger(__name__)


def init_opentelemetry(cfg: Settings) -> None:
    endpoint = cfg.observability.otel_endpoint.strip()
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning(
            "otel_sdk_not_installed",
            hint="pip install opentelemetry-sdk opentelemetry-exporter-otlp",
        )
        return

    resource = Resource.create({"service.name": "streamclip-api"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    log.info("otel_initialised", endpoint=endpoint)
