"""Tests for first-run model prefetch (MASTER_TODO §4.8)."""

from __future__ import annotations

import sys
import time
import types
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import core.model_prefetch as mp
from backend.main import create_app
from core.config import get_settings


@pytest.fixture(autouse=True)
def reset_prefetch_state():
    with mp._lock:
        mp._status.clear()
        mp._thread = None
    yield
    with mp._lock:
        mp._status.clear()
        mp._thread = None


def _wait_done(timeout: float = 5.0) -> dict[str, mp.ModelStatus]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        snap = mp.snapshot()
        if snap and all(s["state"] not in ("pending", "downloading") for s in snap.values()):
            return snap
        time.sleep(0.02)
    raise AssertionError(f"prefetch did not finish: {mp.snapshot()}")


def test_prefetch_marks_ready_and_failed():
    loaders = {
        "good": lambda cfg: "ok-model",
        "bad": lambda cfg: (_ for _ in ()).throw(RuntimeError("download failed")),
    }
    with patch.object(mp, "_LOADERS", loaders):
        assert mp.start_prefetch(get_settings()) is True
        snap = _wait_done()

    assert snap["good"]["state"] == "ready"
    assert snap["good"]["detail"] == "ok-model"
    assert snap["bad"]["state"] == "failed"
    assert "download failed" in snap["bad"]["detail"]


def test_prefetch_missing_dependency_is_skipped():
    def _import_error(cfg):
        raise ImportError(name="ultralytics")

    with patch.object(mp, "_LOADERS", {"yolo": _import_error}):
        mp.start_prefetch(get_settings())
        snap = _wait_done()

    assert snap["yolo"]["state"] == "skipped"
    assert "ultralytics" in snap["yolo"]["detail"]


def test_load_whisper_invokes_faster_whisper():
    cfg = get_settings(reload=True)
    with patch("faster_whisper.WhisperModel") as cls:
        detail = mp._load_whisper(cfg)
    cls.assert_called_once()
    assert "faster-whisper" in detail


def test_load_yolo_invokes_ultralytics():
    cfg = get_settings(reload=True)
    fake = types.ModuleType("ultralytics")
    fake.YOLO = MagicMock(return_value=object())
    with patch.dict(sys.modules, {"ultralytics": fake}):
        detail = mp._load_yolo(cfg)
    fake.YOLO.assert_called_once_with("yolo11n.pt")
    assert detail == "yolo11n"


def test_load_embedder_invokes_sentence_transformers():
    cfg = get_settings(reload=True)
    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = MagicMock(return_value=object())
    with patch.dict(sys.modules, {"sentence_transformers": fake}):
        detail = mp._load_embedder(cfg)
    fake.SentenceTransformer.assert_called_once_with("all-MiniLM-L6-v2")
    assert detail == "all-MiniLM-L6-v2"


def test_start_prefetch_is_idempotent_while_running():
    started = {"n": 0}

    def _slow(cfg):
        started["n"] += 1
        time.sleep(0.3)
        return "slow"

    with patch.object(mp, "_LOADERS", {"slow": _slow}):
        assert mp.start_prefetch(get_settings()) is True
        assert mp.start_prefetch(get_settings()) is False
        _wait_done()

    assert started["n"] == 1


@pytest.mark.asyncio
async def test_health_models_endpoint_empty_is_ready():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["models"] == {}


@pytest.mark.asyncio
async def test_health_models_endpoint_reports_progress():
    with patch.object(mp, "_LOADERS", {"whisper": lambda cfg: "tiny"}):
        mp.start_prefetch(get_settings())
        _wait_done()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health/models")
    body = resp.json()
    assert body["ready"] is True
    assert body["models"]["whisper"]["state"] == "ready"


@pytest.mark.asyncio
async def test_health_models_ready_when_all_failed():
    with patch.object(
        mp,
        "_LOADERS",
        {"bad": lambda cfg: (_ for _ in ()).throw(RuntimeError("boom"))},
    ):
        mp.start_prefetch(get_settings())
        _wait_done()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health/models")
    body = resp.json()
    assert body["ready"] is True
    assert body["models"]["bad"]["state"] == "failed"
