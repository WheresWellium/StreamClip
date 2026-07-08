"""Remaining pipeline_tasks line gaps — webhooks, training export, splice, _safe_async."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.models import ClipStatus
from core.errors import StreamClipError
from core.models import Transcript
from core.tasks import pipeline_tasks as pt


def _asyncio_run(coro):
    return asyncio.run(coro)


def _make_job(**kw):
    defaults = dict(
        id="job1",
        source_url="https://example.com/v",
        source_storage_key=None,
        config_snapshot={"target_clips": 2},
        source_title="t",
        source_duration_secs=120.0,
        source_width=1920,
        source_height=1080,
        owner_id="user1",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_clip(**kw):
    defaults = dict(
        id="clip1",
        job_id="job1",
        rank=0,
        start_secs=0.0,
        end_secs=10.0,
        title="Title",
        hook="hook",
        emotion="hype",
        transcript_text="wow",
        llm_reason="r",
        llm_score=0.5,
        audio_score=0.1,
        spectral_score=0.2,
        flow_score=0.3,
        chat_score=0.4,
        ensemble_score=0.6,
        meme_keywords=["a"],
        status=ClipStatus.PENDING,
        final_storage_key=None,
        render_time_secs=0.0,
        file_size_bytes=0,
        duration_secs=10.0,
        kind="clip",
        parent_clip_ids=None,
        render_overrides={},
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


@pytest.fixture(autouse=True)
def _patch_safe():
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


def test_safe_async_runtime_error_falls_back_to_asyncio_run():
    async def coro():
        return 99

    with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
        with patch("asyncio.run", side_effect=lambda c: 99) as run:
            assert pt._safe_async(coro()) == 99
            run.assert_called_once()


def test_finalise_job_dispatches_training_export(mock_db_cm):
    job = _make_job()
    owner = SimpleNamespace(
        webhook_url=None,
        webhook_secret=None,
        data_contribution_opt_in=True,
    )
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "UserRepository") as UR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        ur = MagicMock()
        ur.get = AsyncMock(return_value=owner)
        ur.increment_minutes_processed = AsyncMock()
        UR.return_value = ur
        with patch.object(pt, "publish_progress"):
            with patch.object(pt, "dispatch_task_by_name") as dispatch:
                pt.finalise_job.run([{"status": "done"}], "job1")
                dispatch.assert_called_once_with(
                    "core.tasks.notify_tasks.export_training_bundle",
                    args=("job1",),
                    queue="default",
                )


def test_splice_clips_insufficient_parents(mock_db_cm):
    splice = _make_clip(
        id="s1",
        kind="splice",
        rank=2,
        parent_clip_ids=["p1"],
    )
    parent = _make_clip(id="p1", final_storage_key="k1")
    job = _make_job()
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(
            side_effect=lambda cid, **kw: splice if cid == "s1" else parent if cid == "p1" else None,
        )
        clips.mark_status = AsyncMock()
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        with patch.object(pt, "_mark_clip_error", new_callable=AsyncMock):
            out = pt.splice_clips.run("job1", "s1")
    assert out["status"] == "error"


def test_process_clip_user_webhook_on_success(tmp_path, monkeypatch, mock_db_cm):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = _make_job(owner_id="user1")
    clip = _make_clip()
    owner = SimpleNamespace(webhook_url="https://hooks.example/clip", webhook_secret="sec")
    final = tmp_path / "jobs" / "job1" / "clip_00_final.mp4"
    transcript = Transcript(segments=[], language="en", duration=10.0, source_path=Path("x"))

    def touch_files(_tmp):
        for name in ("clip_00_raw.mp4", "clip_00_vertical.mp4", "clip_00_captioned.mp4", "clip_00_final.mp4"):
            p = tmp_path / "jobs" / "job1" / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x" * 32)

    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR, \
         patch.object(pt, "AssetRepository") as AR, patch.object(pt, "UserRepository") as UR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=clip)
        clips.mark_status = AsyncMock()
        clips.update_storage_keys = AsyncMock()
        clips.add_overlay = AsyncMock()
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        AR.return_value = MagicMock(list_for_user=AsyncMock(return_value=[]))
        UR.return_value = MagicMock(get=AsyncMock(return_value=owner))
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch.object(pt, "make_storage", return_value=MagicMock()):
                with patch.object(pt, "extract_segment", side_effect=lambda *a, **k: touch_files(tmp_path)):
                    with patch.object(pt, "reframe"):
                        with patch.object(pt, "load_job_transcript", return_value=transcript):
                            with patch.object(pt, "transcribe_clip", side_effect=RuntimeError("no")):
                                with patch.object(pt, "generate_captions"):
                                    with patch.object(pt, "apply_overlays", return_value=(final, [])):
                                        with patch.object(pt, "validate_output_duration", return_value=True):
                                            with patch.object(pt, "subprocess") as sp:
                                                sp.run.return_value = MagicMock(returncode=0)
                                                touch_files(tmp_path)
                                                final.write_bytes(b"x" * 32)
                                                with patch.object(pt.cfg.webhooks, "enabled", False):
                                                    with patch(
                                                        "core.webhooks.deliver_clip_webhook",
                                                    ) as wh:
                                                        out = pt.process_clip.run("job1", "clip1", force=True)
                                                        assert out["status"] == "done"
                                                        wh.assert_called_once()
