"""Brief H3 — close remaining §3.7 line gaps in core.tasks.pipeline_tasks.

Targets:
  • run_transcribe confidence_rerun block (refined / skipped / error)
  • process_clip duration-mismatch raise + fail-path user webhook
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.models import ClipStatus
from core.models import Transcript
from core.tasks import pipeline_tasks as pt


def _asyncio_run(coro):
    return asyncio.run(coro)


def _make_job(**kw):
    defaults = dict(
        id="job1",
        source_url="https://example.com/v",
        source_storage_key="src/key",
        config_snapshot={"target_clips": 2, "processing_tier": "long"},
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
        caption_style="none",
        reframe_preset=None,
        aspect_ratio=None,
        render_overrides=None,
        force_reframe=False,
        source_storage_key=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(pt, "db_session", return_value=cm):
        yield session


@pytest.fixture(autouse=True)
def _patch_safe_async():
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        yield


def _run_transcribe_with_rerun(
    *,
    tmp_path,
    monkeypatch,
    mock_db_cm,
    rerun_side_effect=None,
    rerun_return=None,
):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.whisper, "confidence_rerun_enabled", True)
    job = _make_job(source_url=None)
    transcript = Transcript(segments=[], language="en", duration=1.0, source_path=Path("x"))
    refined = Transcript(segments=[], language="en", duration=1.0, source_path=Path("y"))

    jobs = MagicMock()
    jobs.get = AsyncMock(return_value=job)
    jobs.update_status = AsyncMock()

    rerun_kw = {}
    if rerun_side_effect is not None:
        rerun_kw["side_effect"] = rerun_side_effect
    else:
        rerun_kw["return_value"] = rerun_return if rerun_return is not None else (refined, 2)

    with (
        patch.object(pt, "JobRepository", return_value=jobs),
        patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"),
        patch.object(pt, "transcribe", return_value=transcript),
        patch.object(pt, "make_storage", return_value=MagicMock()),
        patch.object(pt, "save_transcript_json"),
        patch("core.wer_estimate.estimate_wer_proxy", return_value=0.12),
        patch(
            "core.transcribe_confidence.rerun_low_confidence_segments",
            **rerun_kw,
        ) as rerun,
        patch("core.pipeline_metrics.CONFIDENCE_RERUN_TOTAL") as metric,
    ):
        metric.labels.return_value = MagicMock()
        out = pt.run_transcribe.run("job1")
    assert out == "job1"
    return rerun, metric


def test_run_transcribe_confidence_rerun_refined(tmp_path, monkeypatch, mock_db_cm):
    refined = Transcript(segments=[], language="en", duration=1.0, source_path=Path("y"))
    rerun, metric = _run_transcribe_with_rerun(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mock_db_cm=mock_db_cm,
        rerun_return=(refined, 3),
    )
    rerun.assert_called_once()
    metric.labels.assert_any_call(outcome="refined")


def test_run_transcribe_confidence_rerun_skipped(tmp_path, monkeypatch, mock_db_cm):
    base = Transcript(segments=[], language="en", duration=1.0, source_path=Path("x"))
    _rerun, metric = _run_transcribe_with_rerun(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mock_db_cm=mock_db_cm,
        rerun_return=(base, 0),
    )
    metric.labels.assert_any_call(outcome="skipped")


def test_run_transcribe_confidence_rerun_error(tmp_path, monkeypatch, mock_db_cm):
    _rerun, metric = _run_transcribe_with_rerun(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mock_db_cm=mock_db_cm,
        rerun_side_effect=RuntimeError("rerun boom"),
    )
    metric.labels.assert_any_call(outcome="error")


def test_process_clip_duration_mismatch_raises_and_webhooks(
    tmp_path, monkeypatch, mock_db_cm,
):
    """Reach validate_output_duration=False so the StreamClipError raise executes."""
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.webhooks, "enabled", False)

    job = _make_job()
    clip = _make_clip()
    owner = SimpleNamespace(webhook_url="https://hooks.example/fail", webhook_secret="sec")
    transcript = Transcript(segments=[], language="en", duration=10.0, source_path=Path("x"))
    workspace = tmp_path / "jobs" / "job1"
    workspace.mkdir(parents=True, exist_ok=True)
    final = workspace / "clip_00_final.mp4"

    def _touch(*_a, **_k):
        for name in (
            "clip_00_raw.mp4",
            "clip_00_vertical.mp4",
            "clip_00_captioned.mp4",
            "clip_00_final.mp4",
        ):
            (workspace / name).write_bytes(b"x" * 32)

    clips = MagicMock()
    clips.get = AsyncMock(return_value=clip)
    clips.mark_status = AsyncMock()
    clips.update = AsyncMock()
    jobs = MagicMock()
    jobs.get = AsyncMock(return_value=job)
    users = MagicMock()
    users.get = AsyncMock(return_value=owner)

    with (
        patch.object(pt, "ClipRepository", return_value=clips),
        patch.object(pt, "JobRepository", return_value=jobs),
        patch.object(pt, "AssetRepository", return_value=MagicMock(list_for_user=AsyncMock(return_value=[]))),
        patch.object(pt, "UserRepository", return_value=users),
        patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"),
        patch.object(pt, "make_storage", return_value=MagicMock()),
        patch.object(pt, "extract_segment", side_effect=_touch),
        patch.object(pt, "reframe"),
        patch.object(pt, "load_job_transcript", return_value=transcript),
        patch.object(pt, "generate_captions"),
        patch.object(pt, "records_from_db_assets", return_value=[]),
        patch.object(pt, "apply_overlays", return_value=(final, [])),
        patch.object(pt, "validate_output_duration", return_value=False),
        patch.object(pt, "_mark_clip_error", new_callable=AsyncMock),
        patch("core.webhooks.deliver_clip_webhook") as deliver,
    ):
        out = pt.process_clip.run("job1", "clip1", force=True)

    assert out["status"] == "error"
    assert "duration" in (out.get("error") or "").lower() or "unexpected" in (
        out.get("error") or ""
    ).lower()
    deliver.assert_called_once()
    assert deliver.call_args.kwargs.get("status") == "error" or (
        len(deliver.call_args.args) > 2 and deliver.call_args.args[2] == "error"
    )


def test_process_clip_fail_webhook_when_global_webhooks_enabled(
    tmp_path, monkeypatch, mock_db_cm,
):
    """Fail-path webhook fires via cfg.webhooks.enabled even without user URL."""
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.webhooks, "enabled", True)

    job = _make_job(owner_id=None)
    clip = _make_clip()
    clips = MagicMock()
    clips.get = AsyncMock(return_value=clip)
    clips.mark_status = AsyncMock()
    jobs = MagicMock()
    jobs.get = AsyncMock(return_value=job)

    with (
        patch.object(pt, "ClipRepository", return_value=clips),
        patch.object(pt, "JobRepository", return_value=jobs),
        patch.object(pt, "UserRepository", return_value=MagicMock(get=AsyncMock(return_value=None))),
        patch.object(pt, "_ensure_job_source", side_effect=RuntimeError("source gone")),
        patch.object(pt, "make_storage", return_value=MagicMock()),
        patch.object(pt, "_mark_clip_error", new_callable=AsyncMock),
        patch("core.webhooks.deliver_clip_webhook") as deliver,
    ):
        out = pt.process_clip.run("job1", "clip1", force=True)

    assert out["status"] == "error"
    deliver.assert_called_once()
    assert deliver.call_args.kwargs.get("status") == "error" or (
        len(deliver.call_args.args) > 2 and deliver.call_args.args[2] == "error"
    )
