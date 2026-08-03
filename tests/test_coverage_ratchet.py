"""Targeted tests to ratchet coverage over the 95% gate."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import sse as sse_mod
from backend.services.sse import stream_job_progress, stream_publish_progress
from core import progress_bus as pb_mod
from core.config import get_settings
from core.errors import StreamClipError
from core.progress_bus import reset_progress_bus
from core.tasks import pipeline_tasks as pt


@pytest.fixture
def inprocess_cfg(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    return cfg


@pytest.fixture(autouse=True)
def _fresh_bus():
    reset_progress_bus()
    yield
    reset_progress_bus()


def _asyncio_run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _patch_safe_async():
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        yield


@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(pt, "db_session", return_value=cm):
        yield session


# ─── SSE redis gaps ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stream_publish_snapshot_invalid_json():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="not-json")
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-bad", cfg, heartbeat_secs=100)
        await gen.__anext__()
        frame = await gen.__anext__()
        assert "progress" in frame
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_publish_redis_heartbeat_and_cancel():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    async def get_message(**_kwargs):
        # Real suspension point so the drain task can actually be cancelled;
        # an instantly-resolving AsyncMock never yields to the event loop,
        # which turns the generator's `while True` into an uninterruptible
        # busy loop (heartbeat_secs=0.0 makes every iteration "due").
        await asyncio.sleep(0)
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = get_message
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-hb", cfg, heartbeat_secs=0.0)
        await gen.__anext__()
        hb = await gen.__anext__()
        assert "heartbeat" in hb

        async def drain():
            async for _ in gen:
                pass

        task = asyncio.create_task(drain())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_snapshot_invalid_json_early_return():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="plain")
    mock_pubsub = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-bad", cfg, heartbeat_secs=100)
        await gen.__anext__()
        await gen.__anext__()
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_live_json_decode_and_cancel():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    calls = 0

    async def get_message(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"type": "message", "data": "not-json"}
        if calls == 2:
            return {
                "type": "message",
                "data": json.dumps({"status": "done", "event_id": 2}),
            }
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = get_message
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        chunks = [c async for c in stream_job_progress("job-live", cfg, heartbeat_secs=100)]
    assert any("done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_job_client_cancelled():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    async def get_message(**_kwargs):
        # See test_stream_publish_redis_heartbeat_and_cancel: an instantly
        # resolving AsyncMock never yields to the event loop, which starves
        # task.cancel() delivery. Force a real suspension point.
        await asyncio.sleep(0)
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = get_message
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-cancel", cfg, heartbeat_secs=100)
        await gen.__anext__()

        async def drain():
            async for _ in gen:
                pass

        task = asyncio.create_task(drain())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await gen.aclose()


# ─── Pipeline helpers ────────────────────────────────────────────────────────


def test_safe_async_thread_pool_when_loop_running():
    async def coro():
        return 55

    loop = MagicMock()
    loop.is_running.return_value = True
    pool = MagicMock()
    pool.__enter__ = MagicMock(return_value=pool)
    pool.__exit__ = MagicMock(return_value=None)
    pool.submit.return_value.result.return_value = 55

    with patch("asyncio.get_event_loop", return_value=loop):
        with patch("concurrent.futures.ThreadPoolExecutor", return_value=pool):
            assert pt._safe_async(coro()) == 55


def test_apply_clip_overrides_all_keys(monkeypatch):
    clip = SimpleNamespace(render_overrides={
        "caption_style": "minimal",
        "reframe_preset": "talking_head",
        "overlay_enabled": False,
        "aspect_ratio": "16:9",
        "profanity_filter": True,
        "profanity_mode": "bleep",
        "caption_words_per_group": 4,
        "caption_primary_color": "#FF0000",
        "caption_outline_color": "#00FF00",
        "reframe_pan_x": 0.25,
        "reframe_zoom": 1.2,
    })
    pt._apply_clip_overrides(pt.cfg, SimpleNamespace(), clip)
    assert pt.cfg.caption.style == "minimal"
    assert pt.cfg.reframe.preset == "talking_head"
    assert pt.cfg.overlay.enabled is False
    assert pt.cfg.caption.profanity_filter is True
    assert pt.cfg.caption.profanity_mode == "bleep"
    assert pt.cfg.caption.primary_color == "#FF0000"
    assert pt.cfg.caption.outline_color == "#00FF00"
    assert pt.cfg.reframe.pan_x == 0.25
    assert pt.cfg.reframe.zoom == 1.2


def test_run_ingest_upload_progress_message(mock_db_cm):
    from core.ingest.types import SourceKind

    job = SimpleNamespace(
        id="job-up",
        source_url=None,
        source_storage_key="uploads/x.mp4",
        config_snapshot={"target_clips": 1},
        source_title=None,
        source_duration_secs=None,
        source_width=None,
        source_height=None,
        owner_id=None,
    )

    def fake_run(request=None, *, on_progress=None, on_message=None, **_kwargs):
        if on_progress:
            on_progress(0.5)
        if on_message:
            on_message("Copying upload from storage")
        result = MagicMock()
        result.meta.title = "T"
        result.meta.duration = 1.0
        result.meta.width = 1
        result.meta.height = 1
        result.storage_key = "sk"
        result.source_kind = SourceKind.UPLOAD
        result.pipeline_hints = {}
        result.file_size_bytes = None
        result.to_snapshot = lambda: {}
        return result

    reports: list[str] = []

    with patch.object(pt, "JobRepository") as JR, \
         patch.object(pt, "get_redis", return_value=MagicMock()), \
         patch.object(pt, "ensure_pipeline_started"), \
         patch.object(pt, "set_eta_context"), \
         patch.object(pt, "IngestService") as IS, \
         patch.object(pt.run_ingest, "report", side_effect=lambda *a, **kw: reports.append(kw.get("message", ""))):
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        IS.return_value.run = fake_run
        pt.run_ingest.run("job-up")
    assert any("Copying upload" in m for m in reports)


def test_run_ingest_waveform_when_source_exists(tmp_path, monkeypatch, mock_db_cm):
    job = SimpleNamespace(
        id="job-wf",
        source_url="https://example.com/v",
        source_storage_key=None,
        config_snapshot={},
        source_title="t",
        source_duration_secs=10.0,
        source_width=1920,
        source_height=1080,
        owner_id=None,
    )
    source = tmp_path / "jobs" / "job-wf" / "source.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"vid")
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)

    ingest_result = MagicMock()
    ingest_result.meta.title = "T"
    ingest_result.meta.duration = 1.0
    ingest_result.meta.width = 1
    ingest_result.meta.height = 1
    ingest_result.storage_key = None
    from core.ingest.types import SourceKind
    ingest_result.source_kind = SourceKind.URL
    ingest_result.pipeline_hints = {}
    ingest_result.file_size_bytes = None
    ingest_result.to_snapshot = lambda: {}

    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "get_redis", return_value=MagicMock()):
            with patch.object(pt, "ensure_pipeline_started"):
                with patch.object(pt, "set_eta_context"):
                    with patch.object(pt, "IngestService") as IS:
                        IS.return_value.run = MagicMock(return_value=ingest_result)
                        with patch.object(pt, "ensure_job_waveform") as wf:
                            pt.run_ingest.run("job-wf")
                            wf.assert_called_once()


def test_archive_source_upload_failure_logged(tmp_path, monkeypatch):
    source = tmp_path / "jobs" / "j1" / "source.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"x")
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    storage = MagicMock()
    storage.exists.return_value = False
    storage.upload.side_effect = RuntimeError("upload failed")
    with patch.object(pt, "make_storage", return_value=storage):
        assert pt.archive_source_to_storage.run("j1", "archive/key") == "j1"


# ─── Distribution API ────────────────────────────────────────────────────────


def test_ensure_platform_rejects_unknown():
    from backend.api.distribution import _ensure_platform

    with pytest.raises(StreamClipError) as exc:
        _ensure_platform("instagram")
    assert exc.value.code == "unknown_platform"


@pytest.mark.asyncio
async def test_stream_job_redis_cleanup_warning():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-cln", cfg, heartbeat_secs=100)
        await gen.__anext__()
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_publish_inprocess_invalid_json_cleanup(inprocess_cfg):
    """Memory bus: invalid JSON on live channel + generator cleanup."""
    cfg = inprocess_cfg
    bus = pb_mod.get_progress_bus(cfg)
    channel = f"{cfg.redis.publish_pubsub_channel_prefix}pj-mem-inv"
    queue = bus.subscribe(channel)

    async def publish_bad():
        await asyncio.sleep(0.02)
        queue.put_nowait("not-valid-json{{{")
        bus.publish(channel, {"status": "done", "stage": "done", "progress": 1.0})

    task = asyncio.create_task(publish_bad())
    try:
        chunks = [c async for c in stream_publish_progress("pj-mem-inv", cfg, heartbeat_secs=100)]
    finally:
        await task
    assert any("done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_redis_cleanup_exception():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup fail"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-clean-fail", cfg, heartbeat_secs=100)
        await gen.__anext__()
        await gen.aclose()


def test_run_highlights_censors_when_profanity_enabled(mock_db_cm, tmp_path, monkeypatch):
    from core.models import ClipCandidate, Emotion, SignalScores, Transcript, TranscriptSegment

    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = SimpleNamespace(
        id="job1", source_url="https://x", source_storage_key="k",
        config_snapshot={
            "target_clips": 1,
            "profanity_filter": True,
            "profanity_mode": "mask",
        },
        owner_id=None,
    )
    seg = TranscriptSegment(id=0, text="hi", start=0.0, end=5.0, words=())
    transcript = Transcript(segments=[seg], language="en", duration=60.0, source_path=tmp_path / "x")
    cand = ClipCandidate(
        segment_id=0, start=0.0, end=5.0, text="hi",
        scores=SignalScores(), llm_hook="bad hook", llm_title="bad title",
        emotion=Emotion.HYPE,
    )

    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "ClipRepository") as CR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        clips = MagicMock()
        clips.create = AsyncMock(return_value=SimpleNamespace(id="newclip"))
        CR.return_value = clips
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "v.mp4"):
            with patch.object(pt, "make_storage", return_value=MagicMock()):
                with patch.object(pt, "load_job_transcript", return_value=transcript):
                    with patch.object(pt, "find_highlights", return_value=[cand]):
                        with patch.object(pt, "censor_text", side_effect=lambda t, *_a, **_k: f"[{t}]") as cens:
                            assert pt.run_highlights.run("job1") == "job1"
                            assert cens.call_count >= 2
