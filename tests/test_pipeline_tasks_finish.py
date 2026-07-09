"""Finish the three remaining pipeline_tasks line misses (106, 849, 955)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.errors import StreamClipError
from core.tasks import pipeline_tasks as pt


def _asyncio_run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(pt, "db_session", return_value=cm):
        yield session


# ─── Line 106: idle loop path ────────────────────────────────────────────────


def test_safe_async_uses_run_until_complete_on_idle_loop():
    """Line 106: when loop exists and is not running, use run_until_complete."""
    async def coro():
        return 99

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        assert not loop.is_running()
        # Call directly — no autouse patch for this test
        result = pt._safe_async(coro())
        assert result == 99
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())


# ─── Line 849: validate_output_duration failure ──────────────────────────────


def _make_clip_ns(**kwargs):
    defaults = dict(
        id="clip-dur",
        job_id="job-dur",
        start_secs=0.0,
        end_secs=30.0,
        title="Clip",
        rank=0,
        status="pending",
        caption_style="none",
        reframe_preset=None,
        aspect_ratio=None,
        render_overrides=None,
        final_storage_key=None,
        overlay_signature=None,
        force_reframe=False,
        source_storage_key=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_job_ns(**kwargs):
    defaults = dict(
        id="job-dur",
        owner_id=None,
        source_storage_key=None,
        config_snapshot={},
        source_url="https://x",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_process_clip_duration_mismatch_raises(mock_db_cm):
    """Line 849: validate_output_duration returning False raises StreamClipError."""
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        job = _make_job_ns()
        clip = _make_clip_ns()

        jobs_repo = MagicMock()
        jobs_repo.get = AsyncMock(return_value=job)
        clips_repo = MagicMock()
        clips_repo.get = AsyncMock(return_value=clip)
        clips_repo.mark_status = AsyncMock()
        clips_repo.update = AsyncMock()

        fake_path = MagicMock(spec=Path)
        fake_path.__truediv__ = lambda self, x: fake_path
        fake_path.exists.return_value = True

        with (
            patch.object(pt, "JobRepository", return_value=jobs_repo),
            patch.object(pt, "ClipRepository", return_value=clips_repo),
            patch.object(pt, "AssetRepository", return_value=MagicMock(list_for_user=AsyncMock(return_value=[]))),
            patch.object(pt, "UserRepository", return_value=MagicMock(get=AsyncMock(return_value=None))),
            patch.object(pt, "_local_workspace", return_value=fake_path),
            patch.object(pt, "_ensure_job_source", return_value=fake_path),
            patch.object(pt, "make_storage", return_value=MagicMock()),
            patch.object(pt, "extract_segment"),
            patch("core.reframe.reframe", return_value=None),
            patch.object(pt, "generate_captions", return_value=fake_path),
            patch.object(pt, "records_from_db_assets", return_value=[]),
            patch.object(pt, "apply_overlays", return_value=(fake_path, [])),
            patch.object(pt, "validate_output_duration", return_value=False),
            patch.object(pt, "_mark_clip_error", new_callable=AsyncMock),
            patch("core.webhooks.deliver_clip_webhook", return_value=None),
        ):
            result = pt.process_clip.run("job-dur", "clip-dur")
        assert result["status"] == "error"


# ─── Line 955: error delivers user webhook ───────────────────────────────────


def test_process_clip_error_delivers_user_webhook(mock_db_cm):
    """Lines 954-955: when user has webhook_url, deliver_clip_webhook called on failure."""
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        owner = SimpleNamespace(webhook_url="https://hook.example/abc", webhook_secret="sec")
        job = _make_job_ns(id="job-hook", owner_id="user-hook")
        clip = _make_clip_ns(id="clip-hook", job_id="job-hook")

        jobs_repo = MagicMock()
        jobs_repo.get = AsyncMock(return_value=job)
        clips_repo = MagicMock()
        clips_repo.get = AsyncMock(return_value=clip)
        clips_repo.mark_status = AsyncMock()
        users_repo = MagicMock()
        users_repo.get = AsyncMock(return_value=owner)

        fake_path = MagicMock(spec=Path)
        fake_path.__truediv__ = lambda self, x: fake_path

        with (
            patch.object(pt, "JobRepository", return_value=jobs_repo),
            patch.object(pt, "ClipRepository", return_value=clips_repo),
            patch.object(pt, "AssetRepository", return_value=MagicMock(list_for_user=AsyncMock(return_value=[]))),
            patch.object(pt, "UserRepository", return_value=users_repo),
            patch.object(pt, "_local_workspace", return_value=fake_path),
            patch.object(pt, "_ensure_job_source", side_effect=StreamClipError("source missing")),
            patch.object(pt, "make_storage", return_value=MagicMock()),
            patch.object(pt, "_mark_clip_error", new_callable=AsyncMock),
            patch("core.webhooks.deliver_clip_webhook") as mock_deliver,
        ):
            result = pt.process_clip.run("job-hook", "clip-hook")
        assert result["status"] == "error"
        mock_deliver.assert_called_once()
        call_kwargs = mock_deliver.call_args
        # status="error" passed as kwarg
        assert (call_kwargs.kwargs.get("status") == "error"
                or (len(call_kwargs.args) > 2 and call_kwargs.args[2] == "error"))
