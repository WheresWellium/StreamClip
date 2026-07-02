"""Pipeline _run/_safe_async and remaining task branches."""
from __future__ import annotations
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from celery.exceptions import SoftTimeLimitExceeded
from backend.db.models import ClipStatus
from core.models import Transcript, TranscriptSegment
from core.tasks import pipeline_tasks as pt

def _make_clip(**kw):
    defaults = dict(
        id="clip1", job_id="job1", rank=0, start_secs=0.0, end_secs=10.0, title="T", hook="h",
        emotion="hype", transcript_text="wow", llm_reason="r", llm_score=0.5, audio_score=0.1,
        spectral_score=0.2, flow_score=0.3, chat_score=0.4, ensemble_score=0.6, meme_keywords=[],
        status=ClipStatus.PENDING, final_storage_key=None, render_time_secs=0.0, file_size_bytes=0, duration_secs=10.0)
    defaults.update(kw)
    return SimpleNamespace(**defaults)

def test_run_uses_asyncio_run_when_loop_running():
    async def coro():
        return 11
    loop = MagicMock()
    loop.is_running.return_value = True
    with patch("asyncio.get_event_loop", return_value=loop):
        with patch("asyncio.run", return_value=11) as ar:
            assert pt._run(coro()) == 11
            ar.assert_called_once()

def test_run_until_complete_when_loop_idle():
    async def coro():
        return 22
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        assert pt._run(coro()) == 22
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())

def test_safe_async_runtime_error_branch():
    async def coro():
        return 33
    with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
        assert pt._safe_async(coro()) == 33

@pytest.mark.asyncio
async def test_safe_async_nested_running_loop():
    async def coro():
        return 44
    assert pt._safe_async(coro()) == 44

@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(pt, "db_session", return_value=cm):
        yield session

def test_process_clip_successful_transcribe_clip(tmp_path, monkeypatch, mock_db_cm):
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.caption, "refine_clip_transcript", True)
    job = SimpleNamespace(
        id="job1", source_url="u", source_storage_key="k",
        config_snapshot={"caption_style": "gaming_impact", "reframe_preset": "fps_game"},
        source_duration_secs=60.0, owner_id="u1")
    clip = _make_clip()
    transcript = Transcript(segments=[], language="en", duration=10.0, source_path=Path("x"))
    seg_tr = Transcript(segments=[TranscriptSegment(id=0, start=0, end=5, text="hi", words=())], language="en", duration=5.0, source_path=Path("x"))
    final = tmp_path / "jobs" / "job1" / "clip_00_final.mp4"
    final.parent.mkdir(parents=True, exist_ok=True)
    with patch.object(pt, "ClipRepository") as CR, patch.object(pt, "JobRepository") as JR, \
         patch.object(pt, "AssetRepository") as AR:
        clips = MagicMock()
        clips.get = AsyncMock(return_value=clip)
        clips.mark_status = AsyncMock()
        clips.update_storage_keys = AsyncMock()
        clips.add_overlay = AsyncMock()
        CR.return_value = clips
        JR.return_value = MagicMock(get=AsyncMock(return_value=job))
        AR.return_value = MagicMock(list_for_user=AsyncMock(return_value=[]))
        with patch.object(pt, "_ensure_job_source", return_value=tmp_path / "src.mp4"):
            with patch.object(pt, "make_storage", return_value=MagicMock()):
                with patch.object(pt, "extract_segment") as ex:
                    ex.return_value = final.parent / "clip_00_raw.mp4"
                    (final.parent / "clip_00_raw.mp4").write_bytes(b"v")
                    (final.parent / "clip_00_vertical.mp4").write_bytes(b"v")
                    (final.parent / "clip_00_captioned.mp4").write_bytes(b"v")
                    with patch.object(pt, "reframe"):
                        with patch.object(pt, "load_job_transcript", return_value=transcript):
                            with patch.object(pt, "transcribe_clip", return_value=seg_tr):
                                with patch.object(pt, "generate_captions"):
                                    with patch.object(pt, "apply_overlays", return_value=(final, [])):
                                        with patch.object(pt, "validate_output_duration", return_value=True):
                                            with patch.object(pt, "subprocess") as sp:
                                                sp.run.return_value = MagicMock(returncode=0)
                                                final.write_bytes(b"x" * 50)
                                                out = pt.process_clip.run("job1", "clip1")
                                                assert out["status"] == "done"

def test_cleanup_storage_delete_raises(tmp_path, monkeypatch, mock_db_cm):
    from backend.db.models import JobStatus
    monkeypatch.setattr(pt.cfg, "workspace_dir", tmp_path)
    monkeypatch.setattr(pt.cfg.job_retention, "enabled", True)
    job = SimpleNamespace(id="job1", status=JobStatus.DONE, owner_id="u")
    with patch.object(pt, "JobRepository") as JR:
        jobs = MagicMock()
        jobs.list_expired = AsyncMock(return_value=[job])
        jobs.delete = AsyncMock()
        JR.return_value = jobs
        storage = MagicMock()
        storage.list_prefix.return_value = ["jobs/job1/a.mp4"]
        storage.delete.side_effect = RuntimeError("s3 down")
        with patch.object(pt, "make_storage", return_value=storage):
            ws = tmp_path / "jobs" / "job1"
            ws.mkdir(parents=True)
            assert pt.cleanup_expired_jobs.run() == 1
