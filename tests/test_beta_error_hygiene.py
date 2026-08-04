"""Beta Gate B0 — error hygiene tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from core.errors import IngestError, StreamClipError, clip_failure_message, expose_error_context


def test_to_dict_strips_context_outside_development(monkeypatch):
    monkeypatch.setattr("core.errors.expose_error_context", lambda: False)
    err = IngestError("yt-dlp failed", context={"ytdlp_tail": "secret log line"})
    payload = err.to_dict()
    assert "context" not in payload
    assert payload["message"] == err.user_message


def test_to_dict_includes_context_in_development(monkeypatch):
    monkeypatch.setattr("core.errors.expose_error_context", lambda: True)
    err = IngestError("fail", context={"hint": "dev only"})
    payload = err.to_dict()
    assert payload["context"] == {"hint": "dev only"}


def test_clip_failure_message_never_leaks_raw_exception():
    assert clip_failure_message(RuntimeError("CUDA out of memory at foo.py:99")) == (
        "Video processing failed."
    )
    err = IngestError("raw internal")
    assert clip_failure_message(err) == err.user_message


def test_clip_failure_message_rewrites_twitch_live_jargon():
    msg = clip_failure_message(
        RuntimeError("202: live stream unavailable, use a permanent link instead.")
    )
    assert "downloadable VOD" in msg
    assert "202:" not in msg


@pytest.mark.asyncio
async def test_global_500_handler_hides_traceback_in_production(monkeypatch):
    # Production rejects weak AUTH secrets (GAP O8) — use a strong test key.
    monkeypatch.setenv("STREAMCLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("STREAMCLIP_AUTH__SECRET_KEY", "a" * 64)
    import core.config as config_module
    from core.config import get_settings

    config_module._settings = None
    get_settings(reload=True)
    app = create_app()

    @app.get("/api/_test/boom")
    async def _boom():
        raise RuntimeError("super secret traceback detail")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/_test/boom")
    assert res.status_code == 500
    body = res.json()
    assert body["code"] == "internal_error"
    assert "traceback" not in body["message"].lower()
    assert "secret" not in body["message"].lower()


@pytest.mark.asyncio
async def test_http_exception_sanitizes_internal_detail(monkeypatch):
    # Production rejects weak AUTH secrets (GAP O8) — use a strong test key and
    # force a settings reload so create_app() does not reuse a cached env.
    # Do not set STREAMCLIP_CONFIG=desktop.yaml: that mounts the SPA catch-all
    # which intercepts routes registered after create_app().
    monkeypatch.setenv("STREAMCLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("STREAMCLIP_AUTH__SECRET_KEY", "a" * 64)
    import core.config as config_module
    from core.config import get_settings

    config_module._settings = None
    get_settings(reload=True)
    app = create_app()

    @app.get("/api/_test/http-bad")
    async def _http_bad():
        raise HTTPException(status_code=400, detail="ytdlp: ERROR: ffmpeg failed at C:\\tmp\\foo")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/_test/http-bad")
    assert res.status_code == 400
    body = res.json()
    assert "ytdlp" not in body["message"].lower()


def test_streamclip_error_handler_returns_user_message(monkeypatch):
    monkeypatch.setattr("core.errors.expose_error_context", lambda: False)
    err = StreamClipError("internal", user_message="Friendly message", context={"x": 1})
    payload = err.to_dict()
    assert payload["message"] == "Friendly message"
    assert "context" not in payload
