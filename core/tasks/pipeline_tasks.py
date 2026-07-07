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
import shutil
import subprocess
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import structlog
from celery import chain, group
from celery.exceptions import SoftTimeLimitExceeded

from backend.db.models import ClipStatus, JobStatus
from backend.db.repositories import AssetRepository, ClipRepository, JobRepository, UserRepository
from backend.db.session import db_session
from core.captions import generate_captions
from core.celery_app import ProgressTask, celery_app, get_redis, publish_progress, set_eta_context
from core.chat_spikes import ChatEvent
from core.config import get_settings
from core.content_profiles import get_profile
from core.creator_options import (
    DEFAULT_ASPECT_RATIO,
    aspect_ratio_dimensions,
    is_valid_aspect_ratio,
)
from core.errors import StreamClipError
from core.eta import build_eta_context
from core.highlights import find_highlights
from core.ingest.service import IngestService, get_job_source_path
from core.ingest.types import IngestRequest
from core.ingest.waveform import ensure_job_waveform
from core.models import ClipCandidate, Transcript
from core.overlay import apply_overlays, records_from_db_assets
from core.reframe import reframe
from core.ffmpeg_bins import ffmpeg_bin
from core.ffmpeg_utils import extract_segment, validate_output_duration
from core.pipeline_metrics import (
    CLIP_RENDER_SECONDS,
    CLIPS_PROCESSED,
    JOBS_COMPLETED,
    PIPELINE_STAGE_SECONDS,
    WEBHOOK_DELIVERIES,
)
from core.profanity import censor_text
from core.progress_timing import ensure_pipeline_started, finalize_timing
from core.storage import job_key, make_storage
from core.transcribe import load_job_transcript, save_transcript_json, transcribe, transcribe_clip
from core.twitch_chat import fetch_vod_chat
from core.webhooks import deliver_job_webhook
from core.task_runner import apply_async, delay
from core.virality import (
    ClipScoringContext,
    ensemble_with_virality,
    score_clips_virality_parallel,
    select_chat_excerpts,
)

log = structlog.get_logger(__name__)
cfg = get_settings()

# Boot-time caption defaults, captured before any per-job mutation of the
# cfg singleton so jobs without a snapshot key reset instead of inheriting.
_DEFAULT_PROFANITY_FILTER = cfg.caption.profanity_filter
_DEFAULT_PROFANITY_MODE = cfg.caption.profanity_mode
_DEFAULT_WORDS_PER_GROUP = cfg.caption.words_per_group


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


def _webhook_creds_from_owner(owner: Any) -> tuple[str | None, str | None]:
    if owner is None:
        return None, None
    url = owner.webhook_url if isinstance(getattr(owner, "webhook_url", None), str) else None
    secret = owner.webhook_secret if isinstance(getattr(owner, "webhook_secret", None), str) else None
    return url, secret


def _apply_aspect_ratio(value: Any) -> None:
    """Resolve a catalog aspect-ratio id to reframe target dimensions."""
    if not isinstance(value, str) or not is_valid_aspect_ratio(value):
        return
    width, height = aspect_ratio_dimensions(value)
    cfg.reframe.target_width = width
    cfg.reframe.target_height = height


def _apply_clip_overrides(job: Any, clip: Any) -> None:
    """Merge per-clip render overrides into global cfg for this render pass."""
    overrides = getattr(clip, "render_overrides", None) or {}
    if "caption_style" in overrides:
        cfg.caption.style = overrides["caption_style"]
    if "reframe_preset" in overrides:
        cfg.reframe.preset = overrides["reframe_preset"]
    if "overlay_enabled" in overrides:
        cfg.overlay.enabled = bool(overrides["overlay_enabled"])
    if "aspect_ratio" in overrides:
        _apply_aspect_ratio(overrides["aspect_ratio"])
    if "profanity_filter" in overrides:
        cfg.caption.profanity_filter = bool(overrides["profanity_filter"])
    if overrides.get("profanity_mode") in ("mask", "bleep", "omit"):
        cfg.caption.profanity_mode = overrides["profanity_mode"]
    wpg = overrides.get("caption_words_per_group")
    if isinstance(wpg, int) and 1 <= wpg <= 8:
        cfg.caption.words_per_group = wpg


def _apply_job_config(job: Any) -> None:
    """Apply per-job config snapshot to global settings for this task."""
    snap = job.config_snapshot or {}
    if "target_clips" in snap:
        cfg.highlight.target_clips = int(snap["target_clips"])
    if "caption_style" in snap:
        cfg.caption.style = snap["caption_style"]
    if "reframe_preset" in snap:
        cfg.reframe.preset = snap["reframe_preset"]
    if "whisper_model" in snap:
        cfg.whisper.model_size = snap["whisper_model"]
    # Always apply: cfg is a per-process singleton — a missing key must reset
    # to the boot-time default rather than inherit the previous job's setting.
    cfg.caption.profanity_filter = bool(
        snap.get("profanity_filter", _DEFAULT_PROFANITY_FILTER)
    )
    mode = snap.get("profanity_mode")
    cfg.caption.profanity_mode = (
        mode if mode in ("mask", "bleep", "omit") else _DEFAULT_PROFANITY_MODE
    )
    cfg.caption.words_per_group = _DEFAULT_WORDS_PER_GROUP
    # Always apply: cfg is a per-process singleton, so a missing key must
    # reset dimensions rather than inherit the previous job's target.
    _apply_aspect_ratio(snap.get("aspect_ratio", DEFAULT_ASPECT_RATIO))


def _local_workspace(job_id: str) -> Path:
    """Per-job scratch directory."""
    d = cfg.workspace_dir / "jobs" / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextmanager
def _stage_timer(stage: str):
    """Record wall time for a pipeline stage in Prometheus."""
    started = time.perf_counter()
    try:
        yield
    finally:
        PIPELINE_STAGE_SECONDS.labels(stage=stage).observe(time.perf_counter() - started)


def _pipeline_hints_from_job(job: Any) -> dict:
    """Extract ingest-tier hints persisted on the job snapshot."""
    snap = job.config_snapshot or {}
    return {
        k: snap[k]
        for k in (
            "skip_optical_flow",
            "min_clip_duration_override",
            "processing_tier",
            "has_chat_data",
            "content_profile",
            "audio_source",
        )
        if k in snap
    }


def _ensure_job_source(job_id: str, storage_key: str | None) -> Path:
    """Return canonical local source path, downloading from storage if needed."""
    local_source = get_job_source_path(cfg, job_id)
    if local_source.exists():
        return local_source
    if not storage_key:
        raise StreamClipError("No source storage key for job")
    storage = make_storage(cfg)
    local_source.parent.mkdir(parents=True, exist_ok=True)
    storage.download(storage_key, local_source)
    return local_source


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
        run_virality_scores.si(job_id),
        fan_out_clips.si(job_id),
    )
    result = apply_async(workflow)
    log.info("pipeline_dispatched", job_id=job_id, chain_id=result.id)
    return job_id


# ─── 2. Ingest ───────────────────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.run_ingest")
def run_ingest(self: ProgressTask, job_id: str) -> str:
    ensure_pipeline_started(get_redis(), job_id)
    self.report(job_id, stage="ingesting", progress=0.02, message="Preparing source")

    ingest_result: dict[str, Any] = {}

    async def _do() -> None:
        async with db_session() as db:
            jobs = JobRepository(db)
            job = await jobs.get(job_id)
            if job is None:
                raise StreamClipError(f"Job {job_id} not found")

            await jobs.update_status(job_id, JobStatus.INGESTING,
                                     stage="ingesting", progress=0.02)

            if not job.source_url and not job.source_storage_key:
                raise StreamClipError("No source URL or upload key for job")

            is_upload = bool(job.source_storage_key)

            def _on_progress(pct: float) -> None:
                if is_upload:
                    self.report(
                        job_id, stage="ingesting",
                        progress=0.02 + pct * 0.13,
                        message=f"Copying upload {pct:.0%}",
                    )
                else:
                    self.report(
                        job_id, stage="ingesting",
                        progress=0.02 + pct * 0.13,
                        message=f"Downloading {pct:.0%}",
                    )

            def _on_message(msg: str) -> None:
                progress_by_msg = {
                    "Copying upload from storage": 0.02,
                    "Downloading source": 0.02,
                    "Using cached download": 0.14,
                    "Saving to workspace": 0.14,
                    "Uploading archive": 0.14,
                    "Probing video": 0.15,
                }
                self.report(
                    job_id, stage="ingesting",
                    progress=progress_by_msg.get(msg, 0.02),
                    message=msg,
                )

            if job.source_storage_key:
                request = IngestRequest(job_id=job_id, storage_key=job.source_storage_key)
            else:
                request = IngestRequest(job_id=job_id, source_url=job.source_url)

            result = IngestService(cfg).run(
                request, on_progress=_on_progress, on_message=_on_message,
            )

            job.source_title = result.meta.title
            job.source_duration_secs = result.meta.duration
            job.source_width = result.meta.width
            job.source_height = result.meta.height
            job.source_storage_key = result.storage_key

            merged = {**(job.config_snapshot or {}), **result.to_snapshot()}
            job.config_snapshot = merged

            snap = job.config_snapshot or {}
            target_clips = int(snap.get("target_clips", cfg.highlight.target_clips))
            skip_optical = bool(result.pipeline_hints.get("skip_optical_flow", False))
            eta_ctx = build_eta_context(
                duration_secs=result.meta.duration,
                source_kind=result.source_kind.value,
                target_clips=target_clips,
                skip_optical_flow=skip_optical,
                file_size_bytes=result.file_size_bytes,
            )
            set_eta_context(get_redis(), job_id, eta_ctx)

            ingest_result["storage_key"] = result.storage_key
            ingest_result["source_url"] = job.source_url
            ingest_result["defer_upload"] = cfg.ingest.defer_source_upload

            await jobs.update_status(job_id, JobStatus.INGESTING,
                                     stage="ingested", progress=0.15)

    try:
        with _stage_timer("ingest"):
            _safe_async(_do())
    except SoftTimeLimitExceeded:
        publish_progress(job_id, stage="error", progress=0.15,
                        message="Ingest exceeded time limit", status="error")
        raise
    except StreamClipError as exc:
        _mark_error(job_id, exc.code, exc.user_message)
        raise

    storage_key = ingest_result.get("storage_key")
    if (
        ingest_result.get("defer_upload")
        and ingest_result.get("source_url")
        and storage_key
    ):
        delay(archive_source_to_storage, job_id, storage_key)

    # Timeline editor waveform — one cheap showwavespic pass, never fatal.
    source_path = get_job_source_path(cfg, job_id)
    if source_path.exists():
        ensure_job_waveform(job_id, source_path, cfg, make_storage(cfg))

    self.report(job_id, stage="ingested", progress=0.15, message="Source ready")
    return job_id


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="core.tasks.pipeline_tasks.archive_source_to_storage",
)
def archive_source_to_storage(self: ProgressTask, job_id: str, storage_key: str) -> str:
    """Background archival of URL sources to durable storage (non-blocking)."""
    local_source = get_job_source_path(cfg, job_id)
    if not local_source.exists():
        log.warning("archive_source_missing", job_id=job_id, storage_key=storage_key)
        return job_id

    storage = make_storage(cfg)
    if storage.exists(storage_key):
        log.info("archive_source_skip_exists", job_id=job_id, storage_key=storage_key)
        return job_id

    try:
        storage.upload(storage_key, local_source, content_type="video/mp4")
        log.info("archive_source_complete", job_id=job_id, storage_key=storage_key)
    except Exception as exc:
        log.warning("archive_source_failed", job_id=job_id, error=str(exc))
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
            local_source = _ensure_job_source(job_id, job.source_storage_key)

            subtitle_path = None
            if job.source_url:
                from core.ingest.resolvers.url import _url_hash, fetch_subtitles_for_url
                from core.ingest.types import ProcessingTier
                from core.subtitle_import import find_subtitle_file

                tier_name = (job.config_snapshot or {}).get("processing_tier", "long")
                try:
                    tier = ProcessingTier(tier_name)
                except ValueError:
                    tier = ProcessingTier.LONG
                fetch_subtitles_for_url(job.source_url, cfg, tier=tier)
                subtitle_path = find_subtitle_file(cfg.cache_dir, _url_hash(job.source_url))

            transcript = transcribe(local_source, cfg, subtitle_path=subtitle_path)

            # Persist transcript blob to storage for later stages
            storage = make_storage(cfg)
            t_key = job_key(job_id, "transcript", "transcript.json")
            tmp_json = workspace / "transcript.json"
            save_transcript_json(transcript, tmp_json)
            storage.upload(t_key, tmp_json, content_type="application/json")

            await jobs.update_status(job_id, JobStatus.TRANSCRIBING,
                                     stage="transcribed", progress=0.35)

    try:
        with _stage_timer("transcribe"):
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
    self.report(job_id, stage="detecting", progress=0.36, message="Finding clip candidates")

    async def _do() -> list[str]:
        """Returns list of clip IDs created."""
        async with db_session() as db:
            jobs = JobRepository(db)
            clips_repo = ClipRepository(db)
            job = await jobs.get(job_id)
            if job is None:
                raise StreamClipError(f"Job {job_id} not found")

            _apply_job_config(job)

            if job.owner_id:
                owner = await UserRepository(db).get(job.owner_id)
                if owner and owner.style_weights:
                    from core.style_learning import merge_user_style_weights
                    profile = str((job.config_snapshot or {}).get("content_profile", "general"))
                    merged = merge_user_style_weights(profile, owner.style_weights)
                    for key, val in merged.items():
                        setattr(cfg.highlight, key, val)

            await jobs.update_status(job_id, JobStatus.DETECTING,
                                     stage="detecting", progress=0.36)

            workspace = _local_workspace(job_id)
            local_source = _ensure_job_source(job_id, job.source_storage_key)
            storage = make_storage(cfg)

            transcript_obj = load_job_transcript(
                job_id, cfg, storage=storage, source_path=local_source,
            )

            hints = _pipeline_hints_from_job(job)
            chat_cache = workspace / "chat.json"
            candidates = find_highlights(
                transcript_obj,
                local_source,
                cfg,
                pipeline_hints=hints,
                source_url=job.source_url,
                chat_cache_path=chat_cache,
            )

            snap = dict(job.config_snapshot or {})
            snap["has_chat_data"] = chat_cache.exists()
            job.config_snapshot = snap
            await db.flush()

            clip_ids: list[str] = []
            for rank, cand in enumerate(candidates):
                clip_title, clip_hook = cand.llm_title, cand.llm_hook
                if cfg.caption.profanity_filter:
                    pmode = cfg.caption.profanity_mode
                    pwl = cfg.caption.profanity_wordlist
                    clip_title = censor_text(clip_title, pmode, wordlist_path=pwl)
                    clip_hook = censor_text(clip_hook, pmode, wordlist_path=pwl)
                clip = await clips_repo.create(
                    job_id=job_id,
                    rank=rank,
                    start_secs=cand.start,
                    end_secs=cand.end,
                    title=clip_title,
                    hook=clip_hook,
                    emotion=cand.emotion.value,
                    transcript_text=cand.text,
                    llm_reason=cand.llm_reason,
                    ensemble_score=cand.rank_score,
                    llm_score=0.0,
                    audio_score=cand.scores.audio_energy,
                    spectral_score=cand.scores.spectral_novelty,
                    flow_score=cand.scores.optical_flow,
                    chat_score=cand.scores.chat_spikes,
                    duration_secs=cand.duration,
                )
                clip_ids.append(clip.id)
                self.report(
                    job_id,
                    stage="detecting",
                    progress=0.38 + 0.07 * ((rank + 1) / max(len(candidates), 1)),
                    message=f"Discovered clip {rank + 1}",
                    extra={
                        "event": "clip_discovered",
                        "clip_id": clip.id,
                        "rank": rank,
                        "title": clip_title,
                    },
                )

            await jobs.update_status(job_id, JobStatus.DETECTING,
                                     stage="detected", progress=0.45)

            return clip_ids

    try:
        with _stage_timer("highlights"):
            _safe_async(_do())
    except StreamClipError as exc:
        _mark_error(job_id, exc.code, exc.user_message)
        raise

    self.report(job_id, stage="detected", progress=0.45,
                message="Clip candidates ready")
    return job_id


# ─── 4b. Post-hoc virality scoring ───────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.run_virality_scores")
def run_virality_scores(self: ProgressTask, job_id: str) -> str:
    """Score viral potential for each clip after discovery — never gates creation."""
    self.report(job_id, stage="scoring_virality", progress=0.46,
                message="Scoring clip virality")

    async def _do() -> None:
        async with db_session() as db:
            jobs = JobRepository(db)
            clips_repo = ClipRepository(db)
            job = await jobs.get(job_id)
            if job is None:
                raise StreamClipError(f"Job {job_id} not found")

            _apply_job_config(job)
            hints = _pipeline_hints_from_job(job)
            skip_flow = bool(hints.get("skip_optical_flow", False))
            has_chat = bool(hints.get("has_chat_data", False))
            profile_name = str(
                (job.config_snapshot or {}).get("content_profile", "general"),
            )
            profile = get_profile(profile_name)

            clips = await clips_repo.list_for_job(job_id)
            total = max(len(clips), 1)

            chat_events: list[ChatEvent] = []
            if has_chat:
                chat_events = fetch_vod_chat(
                    source_url=job.source_url,
                    cfg=cfg,
                    cache_path=_local_workspace(job_id) / "chat.json",
                )

            transcript_obj: Transcript | None = None
            try:
                transcript_obj = load_job_transcript(
                    job_id, cfg, fallback_transcribe=False,
                )
            except Exception as exc:
                log.warning("virality_context_transcript_unavailable",
                            job_id=job_id, error=str(exc))

            virality_inputs = [
                (clip.transcript_text, clip.start_secs, clip.end_secs)
                for clip in clips
            ]
            contexts: list[ClipScoringContext | None] = []
            for clip in clips:
                before = after = ""
                if transcript_obj is not None:
                    before = transcript_obj.text_in_range(
                        max(0.0, clip.start_secs - 30.0), clip.start_secs,
                    )[-400:]
                    after = transcript_obj.text_in_range(
                        clip.end_secs, clip.end_secs + 30.0,
                    )[:400]
                contexts.append(ClipScoringContext(
                    content_profile=profile_name,
                    audio_score=clip.audio_score,
                    spectral_score=clip.spectral_score,
                    flow_score=None if skip_flow else clip.flow_score,
                    chat_score=clip.chat_score if has_chat else None,
                    chat_excerpts=select_chat_excerpts(
                        chat_events, clip.start_secs, clip.end_secs,
                    ),
                    text_before=before,
                    text_after=after,
                ))
            virality_results = score_clips_virality_parallel(
                virality_inputs, cfg, contexts=contexts,
            )

            for i, (clip, result) in enumerate(zip(clips, virality_results, strict=True)):
                progress = 0.46 + (i / total) * 0.04
                self.report(
                    job_id,
                    stage="scoring_virality",
                    progress=progress,
                    message=f"Virality {i + 1}/{len(clips)}",
                )
                ensemble = ensemble_with_virality(
                    llm_score=result.score,
                    audio_score=clip.audio_score,
                    spectral_score=clip.spectral_score,
                    flow_score=clip.flow_score,
                    chat_score=clip.chat_score,
                    hcfg=cfg.highlight,
                    skip_optical_flow=skip_flow,
                    has_chat=has_chat,
                    profile=profile,
                )
                await clips_repo.update_virality(
                    clip.id,
                    llm_score=result.score,
                    llm_reason=result.reason,
                    emotion=result.emotion.value,
                    ensemble_score=ensemble,
                    meme_keywords=result.meme_keywords,
                )

            await clips_repo.rerank_by_ensemble(job_id)
            await jobs.update_status(
                job_id, JobStatus.PROCESSING,
                stage="virality_scored", progress=0.50,
            )

    try:
        with _stage_timer("virality"):
            _safe_async(_do())
    except StreamClipError as exc:
        _mark_error(job_id, exc.code, exc.user_message)
        raise

    self.report(job_id, stage="virality_scored", progress=0.50,
                message="Virality scores ready")
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
        apply_async(finalise_job.s([], job_id))
        return job_id

    # Group of parallel process_clip tasks, then a finalise callback
    from celery import chord
    job_workflow = chord(
        group(process_clip.s(job_id, cid) for cid in clip_ids),
        finalise_job.s(job_id),
    )
    apply_async(job_workflow)
    return job_id


# ─── 6. Per-clip processor ───────────────────────────────────────────────────

@celery_app.task(
    bind=True, base=ProgressTask,
    name="core.tasks.pipeline_tasks.process_clip",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def process_clip(self: ProgressTask, job_id: str, clip_id: str, force: bool = False) -> dict[str, Any]:
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

            if not force and clip.status == ClipStatus.DONE and clip.final_storage_key:
                log.info("clip_skip_already_done", clip_id=clip_id, job_id=job_id)
                CLIPS_PROCESSED.labels(status="skipped").inc()
                self.report(
                    job_id,
                    stage=f"process/clip_{clip.rank:02d}",
                    progress=0.85,
                    message=f"Clip {clip.rank + 1} ready",
                    extra={
                        "event": "clip_done",
                        "clip_id": clip_id,
                        "rank": clip.rank,
                        "title": clip.title,
                    },
                )
                return {"clip_id": clip_id, "status": "done", "skipped": True}

            _apply_job_config(job)
            _apply_clip_overrides(job, clip)

            await clips_repo.mark_status(clip_id, ClipStatus.PROCESSING)

            slug = f"clip_{clip.rank:02d}"
            self.report(
                job_id,
                stage=f"process/{slug}",
                progress=0.52,
                message=f"Rendering clip {clip.rank + 1}",
                extra={
                    "event": "clip_processing",
                    "clip_id": clip_id,
                    "rank": clip.rank,
                    "title": clip.title,
                },
            )

            workspace = _local_workspace(job_id)
            local_source = _ensure_job_source(job_id, job.source_storage_key)
            storage = make_storage(cfg)

            # Local paths for this clip's stages
            raw_path       = workspace / f"{slug}_raw.mp4"
            vertical_path  = workspace / f"{slug}_vertical.mp4"
            captioned_path = workspace / f"{slug}_captioned.mp4"
            final_path     = workspace / f"{slug}_final.mp4"

            # ── Extract ──
            duration = clip.end_secs - clip.start_secs
            extract_segment(
                local_source,
                raw_path,
                start_secs=clip.start_secs,
                duration_secs=duration,
                export_cfg=cfg.export,
            )

            # ── Reframe ──
            self.report(job_id, stage=f"reframe/{slug}",
                       progress=0.55, message=f"Reframing clip {clip.rank + 1}")
            cand = _clip_to_candidate(clip)
            reframe(raw_path, vertical_path, cfg, cand)

            # ── Caption ──
            self.report(job_id, stage=f"caption/{slug}",
                       progress=0.70, message=f"Captioning clip {clip.rank + 1}")
            transcript = load_job_transcript(
                job_id, cfg, storage=storage, source_path=local_source,
            )
            overrides = getattr(clip, "render_overrides", None) or {}
            raw_edits = overrides.get("transcript_edits")
            transcript_edits = raw_edits if isinstance(raw_edits, dict) and raw_edits else None
            clip_transcript = None
            # Skip the per-clip Whisper refinement pass when user edits exist:
            # edit indices are anchored to the job-transcript word list, and
            # skipping keeps them aligned (and saves a GPU transcription).
            if cfg.caption.refine_clip_transcript and transcript_edits is None:
                try:
                    clip_transcript = transcribe_clip(raw_path, cfg)
                except Exception as exc:
                    log.warning("clip_transcribe_fallback", error=str(exc))
            generate_captions(
                vertical_path, captioned_path, transcript,
                clip.start_secs, clip.end_secs, cfg, emotion=clip.emotion,
                clip_transcript=clip_transcript,
                transcript_edits=transcript_edits,
            )
            if clip_transcript is not None:
                clip_tx_path = workspace / f"{slug}_transcript.json"
                save_transcript_json(clip_transcript, clip_tx_path)
                tx_key = job_key(job_id, "clips", f"{slug}_transcript.json")
                storage.upload(tx_key, clip_tx_path, content_type="application/json")

            # ── Overlay ──
            self.report(job_id, stage=f"overlay/{slug}",
                       progress=0.85, message=f"Adding overlays to clip {clip.rank + 1}")
            # User-uploaded vault assets (DB rows) join the filesystem manifest;
            # downloads are cached per job workspace so N clips fetch once.
            db_assets = await AssetRepository(db).list_for_user(job.owner_id)
            extra_records = records_from_db_assets(
                db_assets, storage, cache_dir=workspace / "db_assets",
            )
            _, overlays = apply_overlays(
                captioned_path, final_path, cand, cfg, extra_assets=extra_records,
            )

            if not validate_output_duration(final_path, duration):
                raise StreamClipError(
                    f"Rendered clip duration mismatch for {clip_id}",
                    user_message="Clip render produced unexpected duration.",
                )

            # ── Generate thumbnail ──
            thumb_path = workspace / f"{slug}_thumb.jpg"
            subprocess.run([
                ffmpeg_bin(), "-y", "-i", str(final_path),
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

            CLIP_RENDER_SECONDS.observe(render_secs)
            CLIPS_PROCESSED.labels(status="done").inc()

            self.report(
                job_id,
                stage=f"process/{slug}",
                progress=0.85,
                message=f"Clip {clip.rank + 1} ready",
                extra={
                    "event": "clip_done",
                    "clip_id": clip_id,
                    "rank": clip.rank,
                    "title": clip.title,
                },
            )

            from core.webhooks import deliver_clip_webhook
            user_webhook_url, user_webhook_secret = None, None
            if job.owner_id:
                owner = await UserRepository(db).get(job.owner_id)
                user_webhook_url, user_webhook_secret = _webhook_creds_from_owner(owner)
            if cfg.webhooks.enabled or user_webhook_url:
                deliver_clip_webhook(
                    job_id=job_id,
                    clip_id=clip_id,
                    status="done",
                    cfg=cfg.webhooks,
                    extra={"render_secs": render_secs},
                    user_webhook_url=user_webhook_url,
                    user_webhook_secret=user_webhook_secret,
                )

            return {"clip_id": clip_id, "status": "done", "render_secs": render_secs}

    try:
        return _safe_async(_do())
    except Exception as exc:
        log.error("clip_failed", clip_id=clip_id, error=str(exc),
                  trace=traceback.format_exc())
        CLIPS_PROCESSED.labels(status="error").inc()
        # Don't propagate — let other clips finish
        _safe_async(_mark_clip_error(clip_id, str(exc)))

        from core.webhooks import deliver_clip_webhook
        async def _clip_fail_hook() -> None:
            async with db_session() as db:
                jobs_repo = JobRepository(db)
                job = await jobs_repo.get(job_id)
                user_webhook_url = None
                user_webhook_secret = None
                if job and job.owner_id:
                    owner = await UserRepository(db).get(job.owner_id)
                    user_webhook_url, user_webhook_secret = _webhook_creds_from_owner(owner)
                if cfg.webhooks.enabled or user_webhook_url:
                    deliver_clip_webhook(
                        job_id=job_id,
                        clip_id=clip_id,
                        status="error",
                        cfg=cfg.webhooks,
                        extra={"error": str(exc)},
                        user_webhook_url=user_webhook_url,
                        user_webhook_secret=user_webhook_secret,
                    )
        _safe_async(_clip_fail_hook())

        return {"clip_id": clip_id, "status": "error", "error": str(exc)}


# ─── 7. Finaliser ────────────────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.finalise_job")
def finalise_job(self: ProgressTask, results: list[dict[str, Any]], job_id: str) -> dict[str, Any]:
    """Mark the job done. Receives the list of per-clip results from the chord."""

    stage_durations = finalize_timing(get_redis(), job_id)

    async def _do() -> dict[str, Any]:
        async with db_session() as db:
            jobs_repo = JobRepository(db)
            users_repo = UserRepository(db)
            job = await jobs_repo.get(job_id)
            done_count = sum(1 for r in results if r.get("status") == "done")
            err_count = sum(1 for r in results if r.get("status") == "error")
            final_status = JobStatus.DONE if err_count == 0 else JobStatus.ERROR
            await jobs_repo.update_status(
                job_id, final_status,
                stage="completed", progress=1.0,
                error_message=f"{err_count} clips failed" if err_count else None,
                stage_durations_json=stage_durations or None,
            )
            if job and job.owner_id and job.source_duration_secs:
                await users_repo.increment_minutes_processed(
                    job.owner_id,
                    job.source_duration_secs / 60.0,
                )
            user_webhook_url = None
            user_webhook_secret = None
            data_opt_in = False
            if job and job.owner_id:
                owner = await users_repo.get(job.owner_id)
                user_webhook_url, user_webhook_secret = _webhook_creds_from_owner(owner)
                data_opt_in = bool(
                    getattr(owner, "data_contribution_opt_in", False),
                )
            return {
                "job_id": job_id,
                "done": done_count,
                "errors": err_count,
                "user_webhook_url": user_webhook_url,
                "user_webhook_secret": user_webhook_secret,
                "data_opt_in": data_opt_in,
            }

    summary = _safe_async(_do())
    terminal = "done" if summary.get("errors", 0) == 0 else "error"
    data_opt_in = summary.pop("data_opt_in", False)
    JOBS_COMPLETED.labels(status=terminal).inc()
    publish_progress(
        job_id, stage="completed", progress=1.0,
        message=f"Done — {summary['done']} clips ready",
        status="done", extra=summary,
    )
    if cfg.webhooks.enabled or summary.get("user_webhook_url"):
        ok = deliver_job_webhook(
            job_id=job_id,
            status=terminal,
            done_count=summary.get("done", 0),
            error_count=summary.get("errors", 0),
            cfg=cfg.webhooks,
            user_webhook_url=summary.get("user_webhook_url"),
            user_webhook_secret=summary.get("user_webhook_secret"),
        )
        WEBHOOK_DELIVERIES.labels(result="success" if ok else "failure").inc()
    # Phase 3c — anonymized training export for opted-in owners (default
    # queue via send_task; avoids importing notify_tasks → circular import).
    if terminal == "done" and data_opt_in:
        celery_app.send_task(
            "core.tasks.notify_tasks.export_training_bundle",
            args=[job_id],
            queue="default",
        )
    return summary


# ─── 9. Splice merged clips ────────────────────────────────────────────────────

@celery_app.task(bind=True, base=ProgressTask, name="core.tasks.pipeline_tasks.splice_clips")
def splice_clips(self: ProgressTask, job_id: str, clip_id: str) -> dict[str, Any]:
    """Merge parent clips into a single vertical output."""

    async def _do() -> dict[str, Any]:
        async with db_session() as db:
            clips_repo = ClipRepository(db)
            jobs_repo = JobRepository(db)
            clip = await clips_repo.get(clip_id, with_overlays=False)
            job = await jobs_repo.get(job_id)
            if clip is None or job is None or clip.kind != "splice":
                raise StreamClipError(f"Splice clip not found: {clip_id}")

            await clips_repo.mark_status(clip_id, ClipStatus.PROCESSING)
            workspace = _local_workspace(job_id)
            storage = make_storage(cfg)

            parent_ids = list(clip.parent_clip_ids or [])
            parents = []
            for pid in parent_ids:
                p = await clips_repo.get(pid, with_overlays=False)
                if p and p.final_storage_key:
                    parents.append(p)

            if len(parents) < 2:
                raise StreamClipError("Not enough parent clips for splice")

            from core.splice import download_clip_finals, splice_clip_files

            keys = [p.final_storage_key for p in parents if p.final_storage_key]
            local_inputs = download_clip_finals(storage, keys, workspace)
            transition = (clip.render_overrides or {}).get("transition", "cut")
            final_path = workspace / f"splice_{clip.rank:02d}_final.mp4"
            splice_clip_files(
                local_inputs,
                final_path,
                cfg,
                transition=str(transition),
            )

            thumb_path = workspace / f"splice_{clip.rank:02d}_thumb.jpg"
            subprocess.run([
                ffmpeg_bin(), "-y", "-i", str(final_path),
                "-ss", "00:00:01", "-vframes", "1",
                "-vf", "scale=540:-1",
                str(thumb_path),
            ], check=True, capture_output=True)

            slug = f"splice_{clip.rank:02d}"
            final_key = job_key(job_id, "clips", f"{slug}_final.mp4")
            thumb_key = job_key(job_id, "clips", f"{slug}_thumb.jpg")
            storage.upload(final_key, final_path, content_type="video/mp4")
            storage.upload(thumb_key, thumb_path, content_type="image/jpeg")

            await clips_repo.update_storage_keys(
                clip_id,
                final=final_key,
                thumbnail=thumb_key,
            )
            clip.duration_secs = sum(p.duration_secs for p in parents)
            clip.file_size_bytes = final_path.stat().st_size
            await clips_repo.mark_status(clip_id, ClipStatus.DONE)
            return {"clip_id": clip_id, "status": "done"}

    try:
        return _safe_async(_do())
    except Exception as exc:
        _safe_async(_mark_clip_error(clip_id, str(exc)))
        return {"clip_id": clip_id, "status": "error", "error": str(exc)}


# ─── 8. Periodic cleanup ─────────────────────────────────────────────────────

@celery_app.task(name="core.tasks.pipeline_tasks.cleanup_expired_jobs")
def cleanup_expired_jobs() -> int:
    """Delete terminal jobs older than retention_days and their storage objects."""
    from datetime import datetime, timedelta, timezone

    retention = cfg.job_retention
    if not retention.enabled:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention.retention_days)

    async def _do() -> int:
        count = 0
        storage = make_storage(cfg)
        async with db_session() as db:
            jobs_repo = JobRepository(db)
            expired = await jobs_repo.list_expired(
                cutoff, limit=retention.batch_size,
            )
            for job in expired:
                prefix = f"jobs/{job.id}/"
                for key in storage.list_prefix(prefix):
                    try:
                        storage.delete(key)
                    except Exception as exc:
                        log.warning("cleanup_storage_delete_failed", key=key, error=str(exc))
                ws = cfg.workspace_dir / "jobs" / job.id
                if ws.exists():
                    shutil.rmtree(ws, ignore_errors=True)
                await jobs_repo.delete(job.id)
                count += 1
            await db.commit()
        return count

    deleted = _safe_async(_do())
    if deleted:
        log.info("cleanup_expired_jobs", deleted=deleted, cutoff=cutoff.isoformat())
    return deleted


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
        meme_keywords=list(clip.meme_keywords or []),
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
