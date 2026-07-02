"""Observability bootstrap."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.config import get_settings
from backend.observability import init_opentelemetry


def test_init_no_endpoint():
    cfg = get_settings(reload=True)
    cfg.observability.otel_endpoint = "  "
    init_opentelemetry(cfg)


def test_init_import_error():
    cfg = get_settings(reload=True)
    cfg.observability.otel_endpoint = "http://otel:4318"
    with patch.dict("sys.modules", {"opentelemetry": None}):
        init_opentelemetry(cfg)


def test_init_success():
    cfg = get_settings(reload=True)
    cfg.observability.otel_endpoint = "http://otel:4318"
    fake_trace = MagicMock()
    with patch.dict("sys.modules", {
        "opentelemetry": MagicMock(trace=fake_trace),
        "opentelemetry.exporter.otlp.proto.http.trace_exporter": MagicMock(),
        "opentelemetry.sdk.resources": MagicMock(),
        "opentelemetry.sdk.trace": MagicMock(),
        "opentelemetry.sdk.trace.export": MagicMock(),
    }):
        init_opentelemetry(cfg)
