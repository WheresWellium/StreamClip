"""Additional pipeline_tasks coverage."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.models import ClipStatus, JobStatus
from core.errors import StreamClipError
from core.models import Emotion, Transcript, TranscriptSegment
from core.tasks import pipeline_tasks as pt


def _asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


def _make_job(**kw):
    defaults = dict(
        id="job1", source_url="https://example.com/v", source_storage_key=None,
        config_snapshot={"target_clips": 2, "caption_style": "gaming_impact", "reframe_preset": "fps_game",
            "whisper_model": "tiny", "skip_optical_flow": True, "content_profile": "gaming"},
        source_title="t", source_duration_secs=120.0, source_width=1920, source_height=1080, owner_id="user1")
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_clip(**kw):
    from backend.db.models import ClipStatus
    defaults = dict(
        id="clip1", job_id="job1", rank=0, start_secs=0.0, end_secs=10.0, title="Title", hook="hook",
        emotion="hype", transcript_text="wow", llm_reason="r", llm_score=0.5, audio_score=0.1,
        spectral_score=0.2, flow_score=0.3, chat_score=0.4, ensemble_score=0.6, meme_keywords=["a"],
        status=ClipStatus.PENDING, final_storage_key=None, render_time_secs=0.0, file_size_bytes=0,
        duration_secs=10.0, kind="clip", parent_clip_ids=None, render_overrides={},
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _ingest_result_mock(**overrides):
    from core.ingest.types import SourceKind
    result = MagicMock()
    result.meta.title = "T"
    result.meta.duration = 1.0
    result.meta.width = 1
    result.meta.height = 1
    result.storage_key = "sk"
    result.source_kind = SourceKind.URL
    result.pipeline_hints = {"skip_optical_flow": True}
    result.file_size_bytes = None
    result.to_snapshot = lambda: {"processing_tier": "short"}
    for key, value in overrides.items():
        setattr(result, key, value)
    return result


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


def test_run_ingest_url_progress_callbacks(mock_db_cm):
    job = _make_job(source_storage_key=None)
    progress_calls: list[float] = []

    def fake_run(request, on_progress=None, on_message=None):
        if on_progress:
            on_progress(0.5)
            progress_calls.append(0.5)
        if on_message:
            on_message("Downloading source")
            on_message("Using cached download")
        return _ingest_result_mock()

    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "get_redis", return_value=MagicMock()):
            with patch.object(pt, "ensure_pipeline_started"):
                with patch.object(pt, "set_eta_context"):
                    with patch.object(pt, "IngestService") as IS:
                        IS.return_value.run = fake_run
                        pt.run_ingest.run("job1")
    assert progress_calls


def test_archive_source_skip_when_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    local = tmp_path / "jobs" / "job1" / "source.mp4"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"x")
    storage = MagicMock()
    storage.exists.return_value = True
    with patch.object(pt, "get_job_source_path", return_value=local):
        with patch.object(pt, "make_storage", return_value=storage):
            assert pt.archive_source_to_storage.run("job1", "key") == "job1"
            storage.upload.assert_not_called()


def test_run_transcribe_with_subtitle_path(mock_db_cm, tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = _make_job(source_url="https://youtube.com/watch?v=abc")
    transcript = Transcript(segments=[], language="en", duration=1.0, source_path=Path("x"))
    sub_path = tmp_path / "subs.en.vtt"
    sub_path.write_text("WEBVTT\n", encoding="utf-8")
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch("core.ingest.resolvers.url.fetch_subtitles_for_url"):
                with patch("core.subtitle_import.find_subtitle_file", return_value=sub_path):
                    with patch.object(pt, "transcribe", return_value=transcript) as tr:
                        with patch.object(pt, "make_storage", return_value=MagicMock()):
                            with patch.object(pt, "save_transcript_json"):
                                pt.run_transcribe.run("job1")
                                assert tr.call_args.kwargs.get("subtitle_path") == sub_path


def test_run_transcribe_invalid_tier(mock_db_cm, tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = _make_job(
        source_url="https://youtube.com/watch?v=abc",
        config_snapshot={"processing_tier": "not_a_tier"},
    )
    transcript = Transcript(segments=[], language="en", duration=1.0, source_path=Path("x"))
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch("core.ingest.resolvers.url.fetch_subtitles_for_url"):
                with patch("core.subtitle_import.find_subtitle_file", return_value=None):
                    with patch.object(pt, "transcribe", return_value=transcript):
                        with patch.object(pt, "make_storage", return_value=MagicMock()):
                            with patch.object(pt, "save_transcript_json"):
                                pt.run_transcribe.run("job1")


def test_run_highlights_job_missing(mock_db_cm):
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=None)
        JR.return_value = jobs
        with patch.object(pt, "_mark_error") as me:
            with pytest.raises(StreamClipError):
                pt.run_highlights.run("job1")
            me.assert_called_once()


def test_run_virality_with_chat_and_transcript(mock_db_cm):
    job = _make_job(
        source_url="https://twitch.tv/v/1",
        config_snapshot={
            "target_clips": 2, "has_chat_data": True, "content_profile": "gaming",
            "skip_optical_flow": True,
        },
    )
    clip = _make_clip()
    seg = TranscriptSegment(id=0, text="context", start=0.0, end=30.0, words=())
    transcript = Transcript(segments=[seg], language="en", duration=60.0, source_path=Path("x"))
    vir = MagicMock(score=0.8, reason="r", emotion=Emotion.HYPE, meme_keywords=["m"])

    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "ClipRepository") as CR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        clips = MagicMock()
        clips.list_for_job = AsyncMock(return_value=[clip])
        clips.update_virality = AsyncMock()
        clips.rerank_by_ensemble = AsyncMock()
        CR.return_value = clips
        with patch.object(pt, "fetch_vod_chat", return_value=[
            SimpleNamespace(offset_secs=5.0, text="chat msg"),
        ]):
            with patch.object(pt, "load_job_transcript", return_value=transcript):
                with patch.object(pt, "score_clips_virality_parallel", return_value=[vir]):
                    with patch.object(pt, "ensemble_with_virality", return_value=1.0):
                        pt.run_virality_scores.run("job1")


def test_run_virality_transcript_load_failure(mock_db_cm):
    job = _make_job(config_snapshot={"target_clips": 1, "skip_optical_flow": True})
    clip = _make_clip()
    vir = MagicMock(score=0.5, reason="r", emotion=Emotion.NEUTRAL, meme_keywords=[])
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "ClipRepository") as CR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        clips = MagicMock()
        clips.list_for_job = AsyncMock(return_value=[clip])
        clips.update_virality = AsyncMock()
        clips.rerank_by_ensemble = AsyncMock()
        CR.return_value = clips
        with patch.object(pt, "load_job_transcript", side_effect=RuntimeError("no transcript")):
            with patch.object(pt, "score_clips_virality_parallel", return_value=[vir]):
                with patch.object(pt, "ensemble_with_virality", return_value=0.5):
                    pt.run_virality_scores.run("job1")


def test_run_virality_job_missing(mock_db_cm):
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=None)
        JR.return_value = jobs
        with patch.object(pt, "_mark_error"):
            with pytest.raises(StreamClipError):
                pt.run_virality_scores.run("missing")


def test_splice_clips_success(tmp_path, monkeypatch, mock_db_cm):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    parent1 = _make_clip(id="p1", rank=0, final_storage_key="k1", duration_secs=5.0)
    parent2 = _make_clip(id="p2", rank=1, final_storage_key="k2", duration_secs=5.0)
    splice = _make_clip(
        id="s1", kind="splice", rank=2, parent_clip_ids=["p1", "p2"],
        render_overrides={"transition": "crossfade"},
    )
    job = _make_job()
    final = tmp_path / "jobs" / "job1" / "splice_02_final.mp4"
    final.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(side_effect=lambda cid, **kw: {
            "s1": splice, "p1": parent1, "p2": parent2,
        }.get(cid))
        clips.mark_status = AsyncMock()
        clips.update_storage_keys = AsyncMock()
        CR.return_value = clips
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        JR.return_value = jobs
        with patch("core.splice.download_clip_finals", return_value=[final, final]):
            with patch("core.splice.splice_clip_files") as splice_fn:
                def write_final(inputs, out, cfg, transition="cut"):
                    out.write_bytes(b"\x00" * 32)
                splice_fn.side_effect = write_final
                with patch.object(pt, "subprocess") as sp:
                    sp.run.return_value = MagicMock(returncode=0)
                    with patch.object(pt, "make_storage", return_value=MagicMock()):
                        out = pt.splice_clips.run("job1", "s1")
                        assert out["status"] == "done"


def test_splice_clips_not_found(mock_db_cm):
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=None)
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=_make_job()))
        with patch.object(pt, "_mark_clip_error", AsyncMock()):
            out = pt.splice_clips.run("job1", "bad")
        assert out["status"] == "error"


def test_cleanup_storage_delete_failure(tmp_path, monkeypatch, mock_db_cm):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.job_retention, "enabled", True)
    job = _make_job()
    job.status = JobStatus.DONE
    storage = MagicMock()
    storage.list_prefix.return_value = ["jobs/job1/a.mp4"]
    storage.delete.side_effect = RuntimeError("s3 down")
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.list_expired = AsyncMock(return_value=[job])
        jobs.delete = AsyncMock()
        JR.return_value = jobs
        ws = tmp_path / "jobs" / "job1"
        ws.mkdir(parents=True)
        with patch.object(pt, "make_storage", return_value=storage):
            assert pt.cleanup_expired_jobs.run() == 1


def test_finalise_user_webhook(mock_db_cm):
    job = _make_job(owner_id="user1")
    user = SimpleNamespace(webhook_url="https://hook.test", webhook_secret="sec")
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "UserRepository") as UR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        ur = MagicMock()
        ur.get = AsyncMock(return_value=user)
        ur.increment_minutes_processed = AsyncMock()
        UR.return_value = ur
        with patch.object(pt, "publish_progress"):
            with patch.object(pt.cfg.webhooks, "enabled", False):
                with patch.object(pt, "deliver_job_webhook", return_value=False) as wh:
                    pt.finalise_job.run([{"status": "done"}], "job1")
                    wh.assert_called_once()
