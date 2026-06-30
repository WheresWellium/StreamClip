"""
StreamClip — Celery Task Chain

The pipeline is decomposed into discrete Celery tasks. Each task:
  • Runs in isolation (own retry policy, own queue)
  • Reads state from Postgres, writes state back to Postgres
  • Pushes progress events to Redis pub/sub for the SSE relay
  • Hands off the job_id to the next task via .chain()

Compared to the old asyncio.gather pipeline, this gives us:
  • Per-stage retry (if transcription fails, ingest is not redone)
  • GPU queue separation (heavy stages get their own worker pool)
  • Crash recovery (a worker dying doesn't lose the job)
  • Horizontal scaling (add more workers, jobs distribute automatically)
"""

from __future__ import annotations

import asyncio
import time
import traceback
from pathlib import Path
from typing import Any

import structlog
from celery import chain, group
from celery.exceptions import SoftTimeLimitExceeded

from backend.db.models import ClipStatus, JobStatus
from backend.db.repositories import ClipRepository, JobRepository
from backend.db.session import db_session
from core.captions import generate_captions
from core.celery_app import ProgressTask, celery_app, publish_progress
from core.config import get_settings
from core.errors import StreamClipError
from core.highlights import find_highlights
from core.ingest import ingest
from core.models import ClipCandidate, Transcript
from core.overlay import apply_overlays
from core.reframe import reframe
from core.storage import job_key, make_storage
from core.transcribe import transcribe

log = structlog.get_logger(__name__)
cfg = get_settings()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _run(coro: Any) -> Any:
    """Run an async coroutine from sync Celery context."""
    return asyncio.get_event_loop().run_until_complete(coro) \
        if asyncio.get_event_loop().is_running() is False \
        else asyncio.run(coro)


def _safe_async(coro: Any) -> Any:
    """Bulletproof async-from-sync runner that handles existing loops."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Nested loop — create a new one in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _apply_job_config(job: Any) -> None:
    """Apply per-job config snapshot to global settings for this task."""
    snap = job.config_snapshot or {}
    if "target_clips" in snap:
        cfg.highlight.target_clips = int(snap["target_clips"])
    if "min_virality_score" in snap:
        cfg.highlight.min_virality_score = int(snap["min_virality_score"])
    if "caption_style" in snap:
        cfg.caption.style = snap["caption_style"]
    if "reframe_preset" in snap:
        cfg.reframe.preset = snap["reframe_preset"]
    if "whisper_model" in snap:
        cfg.whisper.model_size = snap["whisper_model"]


def _local_workspace(job_id: str) -> Path:
    """Per-job scratch directory."""
    d = cfg.workspace_dir / "jobs" / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── 1. Pipeline orchestrator ────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.start_pipeline")
def start_pipeline(self: ProgressTask, job_id: str) -> str:
    """
    Entry point: builds the task chain for a job and dispatches it.
    Returns the chain's async result ID so callers can poll if they want.
    """
    log.info("pipeline_start", job_id=job_id)

    workflow = chain(
        run_ingest.si(job_id),
        run_transcribe.si(job_id),
        run_highlights.si(job_id),
        fan_out_clips.si(job_id),
    )
    result = workflow.apply_async()
    log.info("pipeline_dispatched", job_id=job_id, chain_id=result.id)
    return job_id


# ─── 2. Ingest ───────────────────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.run_ingest")
def run_ingest(self: ProgressTask, job_id: str) -> str:
    self.report(job_id, stage="ingesting", progress=0.02, message="Downloading source")

    async def _do() -> None:
        async with db_session() as db:
            jobs = JobRepository(db)
            job = await jobs.get(job_id)
            if job is None:
                raise StreamClipError(f"Job {job_id} not found")

            await jobs.update_status(job_id, JobStatus.INGESTING,
                                     stage="ingesting", progress=0.02)

            # Resolve source
            source = job.source_url or job.source_storage_key
            if source is None:
                raise StreamClipError("No source URL or upload key for job")

            # If it's a storage key, download it locally first
            workspace = _local_workspace(job_id)
            storage = make_storage(cfg)

            if job.source_storage_key:
                local_source = workspace / f"source_{Path(job.source_storage_key).name}"
                storage.download(job.source_storage_key, local_source)
                source_path = local_source
                source_arg: Any = local_source
            else:
                source_arg = job.source_url

            def _on_progress(pct: float) -> None:
                self.report(job_id, stage="ingesting",
                           progress=0.02 + pct * 0.13,
                           message=f"Downloading {pct:.0%}")

            meta = ingest(source_arg, cfg, on_progress=_on_progress)

            # Update job with metadata
            job.source_title = meta.title
            job.source_duration_secs = meta.duration
            job.source_width = meta.width
            job.source_height = meta.height

            # If we downloaded from URL, push the file into storage too
            if job.source_url and not job.source_storage_key:
                key = job_key(job_id, "source", meta.path.name)
                storage.upload(key, meta.path, content_type="video/mp4")
                job.source_storage_key = key

            await jobs.update_status(job_id, JobStatus.INGESTING,
                                     stage="ingested", progress=0.15)

    try:
        _safe_async(_do())
    except SoftTimeLimitExceeded:
        publish_progress(job_id, stage="error", progress=0.15,
                        message="Ingest exceeded time limit", status="error")
        raise
    except StreamClipError as exc:
        _mark_error(job_id, exc.code, exc.user_message)
        raise

    self.report(job_id, stage="ingested", progress=0.15, message="Source ready")
    return job_id


# ─── 3. Transcribe ───────────────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.run_transcribe")
def run_transcribe(self: ProgressTask, job_id: str) -> str:
    self.report(job_id, stage="transcribing", progress=0.16, message="Transcribing audio")

    async def _do() -> None:
        async with db_session() as db:
            jobs = JobRepository(db)
            job = await jobs.get(job_id)
            if job is None:
                raise StreamClipError(f"Job {job_id} not found")

            await jobs.update_status(job_id, JobStatus.TRANSCRIBING,
                                     stage="transcribing", progress=0.16)

            workspace = _local_workspace(job_id)
            local_source = workspace / f"source_{Path(job.source_storage_key).name}"
            if not local_source.exists():
                storage = make_storage(cfg)
                storage.download(job.source_storage_key, local_source)

            transcript = transcribe(local_source, cfg)

            # Persist transcript blob to storage for later stages
            storage = make_storage(cfg)
            t_key = job_key(job_id, "transcript", "transcript.json")
            from core.transcribe import export_word_level_json
            tmp_json = workspace / "transcript.json"
            export_word_level_json(transcript, tmp_json)
            storage.upload(t_key, tmp_json, content_type="application/json")

            await jobs.update_status(job_id, JobStatus.TRANSCRIBING,
                                     stage="transcribed", progress=0.35)

    try:
        _safe_async(_do())
    except StreamClipError as exc:
        _mark_error(job_id, exc.code, exc.user_message)
        raise

    self.report(job_id, stage="transcribed", progress=0.35,
                message="Transcription complete")
    return job_id


# ─── 4. Highlight detection ──────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.run_highlights")
def run_highlights(self: ProgressTask, job_id: str) -> str:
    self.report(job_id, stage="detecting", progress=0.36, message="Scoring highlights")

    async def _do() -> list[str]:
        """Returns list of clip IDs created."""
        async with db_session() as db:
            jobs = JobRepository(db)
            clips_repo = ClipRepository(db)
            job = await jobs.get(job_id)
            if job is None:
                raise StreamClipError(f"Job {job_id} not found")

            _apply_job_config(job)

            await jobs.update_status(job_id, JobStatus.DETECTING,
                                     stage="detecting", progress=0.36)

            workspace = _local_workspace(job_id)
            local_source = workspace / f"source_{Path(job.source_storage_key).name}"

            # Re-transcribe locally (cached) or load JSON
            transcript_obj = transcribe(local_source, cfg)

            candidates = find_highlights(transcript_obj, local_source, cfg)

            clip_ids: list[str] = []
            for rank, cand in enumerate(candidates):
                clip = await clips_repo.create(
                    job_id=job_id,
                    rank=rank,
                    start_secs=cand.start,
                    end_secs=cand.end,
                    title=cand.llm_title,
                    hook=cand.llm_hook,
                    emotion=cand.emotion.value,
                    transcript_text=cand.text,
                    llm_reason=cand.llm_reason,
                    ensemble_score=cand.rank_score,
                    llm_score=cand.scores.llm_virality,
                    audio_score=cand.scores.audio_energy,
                    spectral_score=cand.scores.spectral_novelty,
                    flow_score=cand.scores.optical_flow,
                    chat_score=cand.scores.chat_spikes,
                    duration_secs=cand.duration,
                )
                clip_ids.append(clip.id)

            await jobs.update_status(job_id, JobStatus.PROCESSING,
                                     stage="rendering", progress=0.50)

            return clip_ids

    try:
        _safe_async(_do())
    except StreamClipError as exc:
        _mark_error(job_id, exc.code, exc.user_message)
        raise

    self.report(job_id, stage="detected", progress=0.50,
                message="Highlights ranked")
    return job_id


# ─── 5. Fan-out: per-clip group ──────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.fan_out_clips")
def fan_out_clips(self: ProgressTask, job_id: str) -> str:
    """Spawn one process_clip task per clip, then a chord finalises the job."""

    async def _get_clip_ids() -> list[str]:
        async with db_session() as db:
            clips_repo = ClipRepository(db)
            clips = await clips_repo.list_for_job(job_id)
            return [c.id for c in clips]

    clip_ids = _safe_async(_get_clip_ids())

    if not clip_ids:
        # No highlights — finalise empty
        finalise_job.apply_async(args=[[], job_id])
        return job_id

    # Group of parallel process_clip tasks, then a finalise callback
    from celery import chord
    job_workflow = chord(
        group(process_clip.s(job_id, cid) for cid in clip_ids),
        finalise_job.s(job_id),
    )
    job_workflow.apply_async()
    return job_id


# ─── 6. Per-clip processor ───────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=ProgressTask,
    name="core.tasks.pipeline_tasks.process_clip",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def process_clip(self: ProgressTask, job_id: str, clip_id: str) -> dict[str, Any]:
    """Process a single clip: extract → reframe → caption → overlay → upload."""

    t0 = time.perf_counter()

    async def _do() -> dict[str, Any]:
        async with db_session() as db:
            clips_repo = ClipRepository(db)
            jobs_repo = JobRepository(db)
            clip = await clips_repo.get(clip_id, with_overlays=False)
            job = await jobs_repo.get(job_id)
            if clip is None or job is None:
                raise StreamClipError(f"Clip/Job not found: {clip_id}/{job_id}")

            _apply_job_config(job)

            await clips_repo.mark_status(clip_id, ClipStatus.PROCESSING)

            workspace = _local_workspace(job_id)
            local_source = workspace / f"source_{Path(job.source_storage_key).name}"
            storage = make_storage(cfg)
            if not local_source.exists():
                storage.download(job.source_storage_key, local_source)

            # Local paths for this clip's stages
            slug = f"clip_{clip.rank:02d}"
            raw_path       = workspace / f"{slug}_raw.mp4"
            vertical_path  = workspace / f"{slug}_vertical.mp4"
            captioned_path = workspace / f"{slug}_captioned.mp4"
            final_path     = workspace / f"{slug}_final.mp4"

            # ── Extract ──
            import subprocess
            duration = clip.end_secs - clip.start_secs
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(clip.start_secs),
                "-i", str(local_source),
                "-t", str(duration),
                "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                "-c:a", "aac", "-b:a", "256k",
                "-pix_fmt", "yuv420p",
                str(raw_path),
            ], check=True, capture_output=True)

            # ── Reframe ──
            self.report(job_id, stage=f"reframe/{slug}",
                       progress=0.55, message=f"Reframing clip {clip.rank + 1}")
            cand = _clip_to_candidate(clip)
            reframe(raw_path, vertical_path, cfg, cand)

            # ── Caption ──
            self.report(job_id, stage=f"caption/{slug}",
                       progress=0.70, message=f"Captioning clip {clip.rank + 1}")
            transcript = transcribe(local_source, cfg)
            generate_captions(
                vertical_path, captioned_path, transcript,
                clip.start_secs, clip.end_secs, cfg, emotion=clip.emotion,
            )

            # ── Overlay ──
            self.report(job_id, stage=f"overlay/{slug}",
                       progress=0.85, message=f"Adding overlays to clip {clip.rank + 1}")
            _, overlays = apply_overlays(captioned_path, final_path, cand, cfg)

            # ── Generate thumbnail ──
            thumb_path = workspace / f"{slug}_thumb.jpg"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(final_path),
                "-ss", "00:00:01", "-vframes", "1",
                "-vf", "scale=540:-1",
                str(thumb_path),
            ], check=True, capture_output=True)

            # ── Upload outputs ──
            keys = {}
            for label, src in (
                ("raw", raw_path),
                ("vertical", vertical_path),
                ("captioned", captioned_path),
                ("final", final_path),
                ("thumbnail", thumb_path),
            ):
                k = job_key(job_id, "clips", f"{slug}_{label}{src.suffix}")
                storage.upload(k, src, content_type="video/mp4" if label != "thumbnail" else "image/jpeg")
                keys[label] = k

            await clips_repo.update_storage_keys(
                clip_id,
                raw=keys["raw"], vertical=keys["vertical"],
                captioned=keys["captioned"], final=keys["final"],
                thumbnail=keys["thumbnail"],
            )

            # Persist overlay metadata
            for ov in overlays:
                await clips_repo.add_overlay(
                    clip_id,
                    trigger_time_secs=ov.trigger_time,
                    duration_secs=ov.duration,
                    position=ov.position,
                    similarity_score=ov.similarity_score,
                    matched_keyword=ov.matched_keyword,
                )

            render_secs = time.perf_counter() - t0
            clip.render_time_secs = render_secs
            clip.file_size_bytes = final_path.stat().st_size
            clip.duration_secs = duration

            await clips_repo.mark_status(clip_id, ClipStatus.DONE)

            return {"clip_id": clip_id, "status": "done", "render_secs": render_secs}

    try:
        return _safe_async(_do())
    except Exception as exc:
        log.error("clip_failed", clip_id=clip_id, error=str(exc),
                  trace=traceback.format_exc())
        # Don't propagate — let other clips finish
        _safe_async(_mark_clip_error(clip_id, str(exc)))
        return {"clip_id": clip_id, "status": "error", "error": str(exc)}


# ─── 7. Finaliser ────────────────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.finalise_job")
def finalise_job(self: ProgressTask, results: list[dict[str, Any]], job_id: str) -> dict[str, Any]:
    """Mark the job done. Receives the list of per-clip results from the chord."""

    async def _do() -> dict[str, Any]:
        async with db_session() as db:
            jobs_repo = JobRepository(db)
            done_count = sum(1 for r in results if r.get("status") == "done")
            err_count = sum(1 for r in results if r.get("status") == "error")
            final_status = JobStatus.DONE if err_count == 0 else JobStatus.ERROR
            await jobs_repo.update_status(
                job_id, final_status,
                stage="completed", progress=1.0,
                error_message=f"{err_count} clips failed" if err_count else None,
            )
            return {"job_id": job_id, "done": done_count, "errors": err_count}

    summary = _safe_async(_do())
    publish_progress(
        job_id, stage="completed", progress=1.0,
        message=f"Done — {summary['done']} clips ready",
        status="done", extra=summary,
    )
    return summary


# ─── 8. Periodic cleanup ─────────────────────────────────────────────────────

@celery_app.task(name="core.tasks.pipeline_tasks.cleanup_expired_jobs")
def cleanup_expired_jobs() -> int:
    """Delete jobs older than 7 days. Returns count of deleted jobs."""
    # Implementation deferred — sketch only
    return 0


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _clip_to_candidate(clip: Any) -> ClipCandidate:
    """Reconstruct a ClipCandidate dataclass from a DB Clip row."""
    from core.models import Emotion, SignalScores
    scores = SignalScores(
        llm_virality=clip.llm_score,
        audio_energy=clip.audio_score,
        spectral_novelty=clip.spectral_score,
        optical_flow=clip.flow_score,
        chat_spikes=clip.chat_score,
    )
    scores.set_ensemble(clip.ensemble_score)
    try:
        emotion = Emotion(clip.emotion)
    except ValueError:
        emotion = Emotion.NEUTRAL
    return ClipCandidate(
        segment_id=clip.rank,
        start=clip.start_secs,
        end=clip.end_secs,
        text=clip.transcript_text,
        scores=scores,
        llm_hook=clip.hook,
        llm_title=clip.title,
        emotion=emotion,
        meme_keywords=[],
        llm_reason=clip.llm_reason,
    )


def _mark_error(job_id: str, code: str, message: str) -> None:
    async def _do() -> None:
        async with db_session() as db:
            jobs_repo = JobRepository(db)
            await jobs_repo.update_status(
                job_id, JobStatus.ERROR,
                stage="error", progress=0.0,
                error_code=code, error_message=message,
            )
    _safe_async(_do())
    publish_progress(job_id, stage="error", progress=0.0,
                    message=message, status="error",
                    extra={"code": code})


async def _mark_clip_error(clip_id: str, message: str) -> None:
    async with db_session() as db:
        clips_repo = ClipRepository(db)
        await clips_repo.mark_status(clip_id, ClipStatus.ERROR, error=message)
