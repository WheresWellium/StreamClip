"""Heavy-mock coverage for core.tasks.pipeline_tasks."""
from __future__ import annotations
import asyncio
import concurrent.futures
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from celery.exceptions import SoftTimeLimitExceeded
from backend.db.models import ClipStatus, JobStatus
from core.errors import StreamClipError
from core.models import ClipCandidate, Emotion, SignalScores, Transcript, TranscriptSegment
from core.tasks import pipeline_tasks as pt

def _asyncio_run(coro):
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
    defaults = dict(
        id="clip1", job_id="job1", rank=0, start_secs=0.0, end_secs=10.0, title="Title", hook="hook",
        emotion="hype", transcript_text="wow", llm_reason="r", llm_score=0.5, audio_score=0.1,
        spectral_score=0.2, flow_score=0.3, chat_score=0.4, ensemble_score=0.6, meme_keywords=["a"],
        status=ClipStatus.PENDING, final_storage_key=None, render_time_secs=0.0, file_size_bytes=0, duration_secs=10.0)
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
def patch_safe_async():
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        yield



def test_apply_job_config_and_hints(tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = _make_job(config_snapshot={
        "target_clips": 5, "caption_style": "minimal_white", "reframe_preset": "irl",
        "whisper_model": "small", "skip_optical_flow": True, "min_clip_duration_override": 8,
        "processing_tier": "short", "has_chat_data": True, "content_profile": "podcast"})
    pt._apply_job_config(job)
    hints = pt._pipeline_hints_from_job(job)
    assert hints["processing_tier"] == "short"
    assert pt._local_workspace("job1").exists()


def test_ensure_job_source_download(tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    local = tmp_path / "jobs" / "job1" / "source.mp4"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"x")
    with patch.object(pt, "get_job_source_path", return_value=local):
        assert pt._ensure_job_source("job1", None) == local
    local.unlink()
    with patch.object(pt, "get_job_source_path", return_value=local):
        storage = MagicMock()
        with patch.object(pt, "make_storage", return_value=storage):
            pt._ensure_job_source("job1", "uploads/key.mp4")
            storage.download.assert_called_once()
    with patch.object(pt, "get_job_source_path", return_value=local):
        with pytest.raises(StreamClipError):
            pt._ensure_job_source("job1", None)


def test_stage_timer_observes():
    with patch.object(pt.PIPELINE_STAGE_SECONDS.labels(stage="x"), "observe") as obs:
        with pt._stage_timer("x"):
            pass
        obs.assert_called_once()


def test_clip_to_candidate_invalid_emotion():
    cand = pt._clip_to_candidate(_make_clip(emotion="not_real"))
    assert cand.emotion == Emotion.NEUTRAL


def test_mark_error_and_clip_error(mock_db_cm):
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "publish_progress"):
            pt._mark_error("job1", "code", "msg")
    with patch.object(pt, "ClipRepository") as CR:
        clips = MagicMock()
        clips.mark_status = AsyncMock()
        CR.return_value = clips
        asyncio.run(pt._mark_clip_error("c1", "e"))


def test_start_pipeline():
    chain_result = MagicMock(id="chain-1")
    with patch.object(pt, "chain") as chain_mock:
        workflow = MagicMock()
        workflow.apply_async.return_value = chain_result
        chain_mock.return_value = workflow
        assert pt.start_pipeline.run("job1") == "job1"


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


def test_run_ingest_success(mock_db_cm):
    job = _make_job()
    ingest_result = _ingest_result_mock()
    mock_redis = MagicMock()
    with patch.object(pt, "get_redis", return_value=mock_redis):
        with patch.object(pt, "ensure_pipeline_started"):
            with patch.object(pt, "set_eta_context"):
                with patch.object(pt, "archive_source_to_storage") as archive:
                    with patch.object(pt, "JobRepository") as JR:
                        jobs = MagicMock()
                        jobs.get = AsyncMock(return_value=job)
                        jobs.update_status = AsyncMock()
                        JR.return_value = jobs
                        with patch.object(pt, "IngestService") as IS:
                            IS.return_value.run.return_value = ingest_result
                            assert pt.run_ingest.run("job1") == "job1"
                            archive.delay.assert_called_once_with("job1", "sk")
    job2 = _make_job(source_url=None, source_storage_key="up/key")
    with patch.object(pt, "get_redis", return_value=mock_redis):
        with patch.object(pt, "ensure_pipeline_started"):
            with patch.object(pt, "set_eta_context"):
                with patch.object(pt, "archive_source_to_storage") as archive_upload:
                    with patch.object(pt, "JobRepository") as JR:
                        jobs = MagicMock()
                        jobs.get = AsyncMock(return_value=job2)
                        jobs.update_status = AsyncMock()
                        JR.return_value = jobs
                        with patch.object(pt, "IngestService") as IS:
                            from core.ingest.types import SourceKind

                            IS.return_value.run.return_value = _ingest_result_mock(
                                source_kind=SourceKind.UPLOAD,
                            )
                            pt.run_ingest.run("job1")
                            archive_upload.delay.assert_not_called()


def test_archive_source_to_storage_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    local = tmp_path / "jobs" / "job1" / "source.mp4"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"video")
    storage = MagicMock()
    storage.exists.return_value = False
    with patch.object(pt, "get_job_source_path", return_value=local):
        with patch.object(pt, "make_storage", return_value=storage):
            assert pt.archive_source_to_storage.run("job1", "jobs/job1/source/source.mp4") == "job1"
    storage.upload.assert_called_once()


def test_archive_source_to_storage_skips_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    local = tmp_path / "jobs" / "job1" / "source.mp4"
    with patch.object(pt, "get_job_source_path", return_value=local):
        with patch.object(pt, "make_storage") as make_storage:
            assert pt.archive_source_to_storage.run("job1", "jobs/job1/source/source.mp4") == "job1"
            make_storage.assert_not_called()


def test_run_ingest_errors(mock_db_cm):
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=None)
        JR.return_value = jobs
        with patch.object(pt, "_mark_error"):
            with pytest.raises(StreamClipError):
                pt.run_ingest.run("job1")
    job = _make_job(source_url=None, source_storage_key=None)
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "_mark_error"):
            with pytest.raises(StreamClipError):
                pt.run_ingest.run("job1")
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=_make_job())
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "IngestService") as IS:
            IS.return_value.run.side_effect = StreamClipError("x", user_message="u")
            with patch.object(pt, "_mark_error") as me:
                with pytest.raises(StreamClipError):
                    pt.run_ingest.run("job1")
                me.assert_called_once()
    with patch.object(pt, "_safe_async", side_effect=SoftTimeLimitExceeded()):
        with patch.object(pt, "publish_progress"):
            with pytest.raises(SoftTimeLimitExceeded):
                pt.run_ingest.run("job1")


def test_run_transcribe(mock_db_cm, tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = _make_job(source_storage_key="src/key")
    transcript = Transcript(segments=[], language="en", duration=1.0, source_path=Path("x"))
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch.object(pt, "transcribe", return_value=transcript):
                with patch.object(pt, "make_storage", return_value=MagicMock()):
                    with patch.object(pt, "save_transcript_json"):
                        assert pt.run_transcribe.run("job1") == "job1"


def test_run_highlights(mock_db_cm, tmp_path, monkeypatch):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    job = _make_job()
    seg = TranscriptSegment(id=0, text="hi", start=0.0, end=5.0, words=())
    transcript = Transcript(segments=[seg], language="en", duration=60.0, source_path=Path("x"))
    cand = ClipCandidate(segment_id=0, start=0.0, end=5.0, text="hi", scores=SignalScores(),
        llm_hook="h", llm_title="t", emotion=Emotion.HYPE)
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "ClipRepository") as CR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        clips = MagicMock()
        clips.create = AsyncMock(return_value=MagicMock(id="newclip"))
        CR.return_value = clips
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "v.mp4"):
            with patch.object(pt, "make_storage", return_value=MagicMock()):
                with patch.object(pt, "load_job_transcript", return_value=transcript):
                    with patch.object(pt, "find_highlights", return_value=[cand]):
                        assert pt.run_highlights.run("job1") == "job1"


def test_run_virality_scores(mock_db_cm):
    job = _make_job()
    clip = _make_clip()
    vir = MagicMock(score=0.9, reason="r", emotion=Emotion.HYPE, meme_keywords=["m"])
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
        with patch.object(pt, "score_clips_virality_parallel", return_value=[vir]):
            with patch.object(pt, "ensemble_with_virality", return_value=1.0):
                assert pt.run_virality_scores.run("job1") == "job1"


def test_fan_out_clips_empty(mock_db_cm):
    with patch.object(pt, "ClipRepository") as CR:
        clips = MagicMock()
        clips.list_for_job = AsyncMock(return_value=[])
        CR.return_value = clips
        with patch.object(pt, "finalise_job") as fj:
            fj.apply_async = MagicMock()
            assert pt.fan_out_clips.run("job1") == "job1"
            fj.apply_async.assert_called_once()


def test_fan_out_clips_with_clips(mock_db_cm):
    with patch.object(pt, "ClipRepository") as CR:
        clips = MagicMock()
        clips.list_for_job = AsyncMock(return_value=[_make_clip(id="c1")])
        CR.return_value = clips
        with patch("celery.chord") as chord_mock:
            workflow = MagicMock()
            chord_mock.return_value = workflow
            with patch.object(pt, "group"):
                assert pt.fan_out_clips.run("job1") == "job1"
            workflow.apply_async.assert_called_once()


def _touch_clip_files(tmp_path):
    base = tmp_path / "jobs" / "job1"
    for s in ("raw", "vertical", "captioned", "final"):
        p = base / f"clip_00_{s}.mp4"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"vid")
    (base / "clip_00_thumb.jpg").write_bytes(b"jpg")


def test_process_clip_paths(tmp_path, monkeypatch, mock_db_cm):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.caption, "refine_clip_transcript", True)
    job = _make_job()
    clip = _make_clip(status=ClipStatus.DONE, final_storage_key="already")
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=clip)
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        out = pt.process_clip.run("job1", "clip1")
        assert out.get("skipped")
    clip2 = _make_clip(status=ClipStatus.PENDING)
    transcript = Transcript(segments=[], language="en", duration=10.0, source_path=Path("x"))
    final = tmp_path / "jobs" / "job1" / "clip_00_final.mp4"
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=clip2)
        clips.mark_status = AsyncMock()
        clips.update_storage_keys = AsyncMock()
        clips.add_overlay = AsyncMock()
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch.object(pt, "make_storage", return_value=MagicMock()):
                with patch.object(pt, "extract_segment", side_effect=lambda *a, **k: _touch_clip_files(tmp_path)):
                    with patch.object(pt, "reframe"):
                        with patch.object(pt, "load_job_transcript", return_value=transcript):
                            with patch.object(pt, "transcribe_clip", side_effect=RuntimeError("no")):
                                with patch.object(pt, "generate_captions"):
                                    ov = MagicMock(trigger_time=0, duration=1, position="top", similarity_score=0.5, matched_keyword="k")
                                    with patch.object(pt, "apply_overlays", return_value=(final, [ov])):
                                        with patch.object(pt, "validate_output_duration", return_value=True):
                                            with patch.object(pt, "subprocess") as sp:
                                                sp.run.return_value = MagicMock(returncode=0)
                                                _touch_clip_files(tmp_path)
                                                final.write_bytes(b"x" * 20)
                                                out = pt.process_clip.run("job1", "clip1")
                                                assert out["status"] == "done"
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=clip2)
        clips.mark_status = AsyncMock()
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        with patch.object(pt, "_ensure_job_source", side_effect=RuntimeError("boom")):
            out = pt.process_clip.run("job1", "clip1")
            assert out["status"] == "error"
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=clip2)
        clips.mark_status = AsyncMock()
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch.object(pt, "make_storage", return_value=MagicMock()):
                with patch.object(pt, "extract_segment", side_effect=lambda *a, **k: _touch_clip_files(tmp_path)):
                    with patch.object(pt, "reframe"):
                        with patch.object(pt, "load_job_transcript", return_value=transcript):
                            with patch.object(pt, "generate_captions"):
                                with patch.object(pt, "apply_overlays", return_value=(final, [])):
                                    with patch.object(pt, "validate_output_duration", return_value=False):
                                        out = pt.process_clip.run("job1", "clip1", force=True)
                                        assert out["status"] == "error"


def test_finalise_job(mock_db_cm):
    job = _make_job()
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "UserRepository") as UR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        users = MagicMock()
        users.increment_minutes_processed = AsyncMock(return_value=None)
        users.get = AsyncMock(return_value=None)
        UR.return_value = users
        with patch.object(pt, "publish_progress"):
            with patch.object(pt.cfg.webhooks, "enabled", False):
                summary = pt.finalise_job.run([{"status": "done"}], "job1")
                assert summary["done"] == 1
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "UserRepository") as UR:
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        ur = MagicMock()
        ur.increment_minutes_processed = AsyncMock(return_value=None)
        ur.get = AsyncMock(return_value=None)
        UR.return_value = ur
        with patch.object(pt, "publish_progress"):
            with patch.object(pt.cfg.webhooks, "enabled", True):
                with patch.object(pt, "deliver_job_webhook", return_value=True):
                    pt.finalise_job.run([{"status": "error"}], "job1")


def test_cleanup_expired_jobs(tmp_path, monkeypatch, mock_db_cm):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.job_retention, "enabled", False)
    assert pt.cleanup_expired_jobs.run() == 0
    monkeypatch.setattr(pt.cfg.job_retention, "enabled", True)
    job = _make_job()
    job.status = JobStatus.DONE
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.list_expired = AsyncMock(return_value=[job])
        jobs.delete = AsyncMock()
        JR.return_value = jobs
        storage = MagicMock()
        storage.list_prefix.return_value = ["jobs/job1/a.mp4"]
        with patch.object(pt, "make_storage", return_value=storage):
            ws = tmp_path / "jobs" / "job1"
            ws.mkdir(parents=True)
            (ws / "x.txt").write_text("x")
            assert pt.cleanup_expired_jobs.run() == 1
