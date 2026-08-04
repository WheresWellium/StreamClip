"""Desktop sidecar defaults OPS_WEBHOOK_URL to henna support-ingest."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.desktop

from desktop_sidecar.run import (  # noqa: E402
    DEFAULT_SUPPORT_COLLECTOR_URL,
    ensure_support_collector_url,
)


@pytest.fixture(autouse=True)
def _clean_support_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPS_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("STREAMCLIP_DISABLE_SUPPORT_COLLECTOR", raising=False)
    monkeypatch.delenv("STREAMCLIP_DESKTOP_DATA_DIR", raising=False)
    monkeypatch.delenv("STREAMCLIP_QUEUE__BACKEND", raising=False)


def test_ensure_support_collector_sets_default_for_inprocess(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STREAMCLIP_QUEUE__BACKEND", "inprocess")
    ensure_support_collector_url()
    assert os.environ["OPS_WEBHOOK_URL"] == DEFAULT_SUPPORT_COLLECTOR_URL


def test_ensure_support_collector_respects_existing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STREAMCLIP_QUEUE__BACKEND", "inprocess")
    monkeypatch.setenv("OPS_WEBHOOK_URL", "https://example.test/hook")
    ensure_support_collector_url()
    assert os.environ["OPS_WEBHOOK_URL"] == "https://example.test/hook"


def test_ensure_support_collector_can_disable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STREAMCLIP_QUEUE__BACKEND", "inprocess")
    monkeypatch.setenv("STREAMCLIP_DISABLE_SUPPORT_COLLECTOR", "1")
    ensure_support_collector_url()
    assert "OPS_WEBHOOK_URL" not in os.environ
