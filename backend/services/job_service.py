"""
StreamClip — Service Layer

Thin business-logic layer between API route handlers and the repositories.
The job creation flow lives here so it's reusable from REST routes, CLI
commands, and any future GraphQL or gRPC surface.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    ALLOWED_AUDIO_UPLOAD_TYPES,
    BatchCreateJobRequest,
    BatchCreateJobResponse,
    CaptionExportOut,
    CaptionExportRequest,
    ClipOut,
    ClipOverlayOut,
    ClipPublishStatusOut,
    ClipWordOut,
    ClipWordsOut,
    CreateJobRequest,
    JobOut,
    PublishClipRequest,
    PublishClipResponse,
    SpliceClipsRequest,
    SpliceClipsResponse,
    TitleSuggestionsResponse,
    TitleSuggestionOut,
    TranscriptSegmentSummaryOut,
    TranscriptTimestampsOut,
    TranscriptWordOut,
    UpdateClipRequest,
    UpdateJobRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from backend.db.models import Clip, ClipStatus, Job, JobStatus
from backend.db.repositories import (
    ClipRepository,
    DeviceRepository,
    JobRepository,
    JobTitleAuditRepository,
    PublishJobRepository,
    UserRepository,
)
from backend.middleware.scope import RequestScope
from core.caption_export import (
    CaptionExportFormat,
    build_export_transcript,
    caption_export_filename,
    export_caption_file,
)
from core.caption_timing import collect_words_for_window
from core.captions import build_ass_for_clip_window, generate_captions
from core.ffmpeg_utils import extract_segment
from core.ingest.service import get_job_source_path
from core.config import Settings
from core.billing import get_tier_limits
from core.creator_options import is_valid_caption_style
from core.errors import InvalidSourceError, JobNotFoundError, QuotaExceededError, StreamClipError
from core.pipeline_metrics import (
    CAPTION_EXPORT_TOTAL,
    CAPTION_PREVIEW_SECONDS,
    TITLE_SUGGESTIONS_TOTAL,
)
from core.title_suggestions import DEFAULT_TONE, VALID_TONES, generate_title_suggestions
from core.storage import Storage, job_key, upload_key
from core.transcript_io import load_persisted_job_transcript

log = structlog.get_logger(__name__)


# ─── Job service ─────────────────────────────────────────────────────────────

class JobService:
    def __init__(self, db: AsyncSession, cfg: Settings, storage: Storage) -> None:
        self.db = db
        self.cfg = cfg
        self.storage = storage
        self.jobs = JobRepository(db)
        self.clips = ClipRepository(db)
        self.publish_jobs = PublishJobRepository(db)
        self.title_audit = JobTitleAuditRepository(db)
        self.users = UserRepository(db)
        self.devices = DeviceRepository(db)

    async def create_job(
        self,
        request: CreateJobRequest,
        scope: RequestScope,
    ) -> Job:
        if not request.source_url and not request.source_upload_key:
            raise InvalidSourceError("Must provide source_url OR source_upload_key")

        owner_id = scope.user_id
        device_id: str | None = None
        if owner_id is None and scope.device_id:
            device = await self.devices.upsert(scope.device_id)
            device_id = device.id  # normalized — keeps the jobs.device_id FK valid

        # Tier quota check — unconditional for authenticated users.
        # Per-minute Redis rate limiting stays in backend/middleware/rate_limit.py
        # and remains gated on cfg.rate_limit.enabled.
        if owner_id:
            user = await self.users.get(owner_id)
            if user:
                limits = get_tier_limits(user.tier)
                if user.jobs_used_this_month >= limits.max_jobs_per_month:
                    raise QuotaExceededError("Monthly job quota exceeded")
                if request.target_clips > limits.max_target_clips:
                    raise QuotaExceededError(
                        f"Your plan allows up to {limits.max_target_clips} clips per job",
                    )
                # Minutes-per-month ceiling; 0 means unlimited, skip check.
                max_mins = limits.max_minutes_per_month
                if max_mins > 0 and user.minutes_processed_this_month >= max_mins:
                    raise QuotaExceededError(
                        f"Monthly minutes quota exceeded. "
                        f"Your plan allows {max_mins:.0f} minutes per month.",
                    )

        # Snapshot the config the job will use. This freezes settings so
        # later config changes don't break repeatability.
        config_snapshot = {
            "target_clips": request.target_clips,
            "caption_style": request.caption_style,
            "reframe_preset": request.reframe_preset,
            "content_profile": request.content_profile,
            "aspect_ratio": request.aspect_ratio,
            "profanity_filter": request.profanity_filter,
            "profanity_mode": request.profanity_mode,
            "whisper_model": self.cfg.whisper.model_size,
            "llm_provider": self.cfg.llm.provider,
            "llm_model": self.cfg.llm.model,
        }

        job = await self.jobs.create(
            owner_id=owner_id,
            device_id=device_id,
            source_url=request.source_url,
            source_storage_key=request.source_upload_key,
            display_title=request.display_title,
            config_snapshot=config_snapshot,
            asset_pack_id=request.asset_pack_id,
            status=JobStatus.QUEUED,
            current_stage="queued",
            progress=0.0,
        )
        if owner_id:
            await self.users.increment_jobs_used(owner_id)
        log.info("job_created", job_id=job.id, owner=owner_id)
        return job

    async def get_job(self, job_id: str, *, scope: RequestScope) -> Job:
        job = await self.jobs.get_for_scope(
            job_id,
            owner_id=scope.user_id,
            device_id=scope.device_id,
            device_scoped=self.cfg.auth.device_scoped_anonymous,
        )
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        # Eager-load clips
        return await self.jobs.get(job_id, with_clips=True)  # type: ignore[return-value]

    async def list_jobs(
        self,
        scope: RequestScope,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Job]:
        from backend.db.models import JobStatus

        job_status = JobStatus(status) if status else None
        return await self.jobs.list_for_scope(
            owner_id=scope.user_id,
            device_id=scope.device_id,
            device_scoped=self.cfg.auth.device_scoped_anonymous,
            limit=limit,
            offset=offset,
            status=job_status,
            search=search,
        )

    async def cancel_job(self, job_id: str, scope: RequestScope) -> None:
        job = await self.jobs.get_for_scope(
            job_id,
            owner_id=scope.user_id,
            device_id=scope.device_id,
            device_scoped=self.cfg.auth.device_scoped_anonymous,
        )
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        if job.celery_task_id and self.cfg.queue.backend != "inprocess":
            # Revoke via broker — skipped in desktop/inprocess mode (no broker)
            from core.celery_app import celery_app
            try:
                celery_app.control.revoke(job.celery_task_id, terminate=True)
            except Exception:
                log.warning("celery_revoke_failed", task_id=job.celery_task_id)
        await self.jobs.cancel(job_id)

    async def update_job(
        self,
        job_id: str,
        body: UpdateJobRequest,
        *,
        scope: RequestScope,
    ) -> tuple[Job, str | None]:
        job = await self.jobs.get_for_scope(
            job_id,
            owner_id=scope.user_id,
            device_id=scope.device_id,
            device_scoped=self.cfg.auth.device_scoped_anonymous,
        )
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        updates = body.model_dump(exclude_unset=True)
        audit_id: str | None = None
        if "display_title" in updates:
            new_title = updates["display_title"]
            previous = job.display_title
            if previous != new_title:
                job.display_title = new_title
                row = await self.title_audit.create(
                    job_id=job_id,
                    previous_title=previous,
                    new_title=new_title,
                    user_id=scope.user_id,
                    source="user_edit",
                )
                audit_id = row.id
                await self.db.flush()
        return await self.get_job(job_id, scope=scope), audit_id

    def _job_transcript_sample(self, job: Job, transcript) -> str:
        if job.clips:
            ranked = sorted(job.clips, key=lambda c: c.ensemble_score, reverse=True)
            for clip in ranked:
                text = (clip.transcript_text or "").strip()
                if text:
                    return text[:4000]
        return " ".join(seg.text for seg in transcript.segments)[:4000]

    def _job_title_metadata(self, job: Job) -> dict[str, str]:
        snapshot = job.config_snapshot or {}
        meta: dict[str, str] = {}
        if job.source_title:
            meta["source_title"] = job.source_title
        profile = snapshot.get("content_profile")
        if profile:
            meta["content_profile"] = str(profile)
        if job.clips:
            top = max(job.clips, key=lambda c: c.ensemble_score)
            if top.emotion:
                meta["top_emotion"] = top.emotion
            if top.meme_keywords:
                meta["keywords"] = ", ".join(top.meme_keywords[:8])
        return meta

    async def get_title_suggestions(
        self,
        job_id: str,
        *,
        scope: RequestScope,
        tone: str = DEFAULT_TONE,
    ) -> TitleSuggestionsResponse:
        job = await self.get_job(job_id, scope=scope)
        if job.status not in (JobStatus.DONE, JobStatus.ERROR):
            exc = StreamClipError(
                "Job not ready for title suggestions",
                user_message="Wait until the job finishes processing before generating titles.",
                code="job_not_ready",
                http_status=409,
            )
            raise exc

        try:
            transcript = await self._load_job_transcript(job_id)
        except StreamClipError:
            TITLE_SUGGESTIONS_TOTAL.labels(status="no_transcript").inc()
            raise

        normalized_tone = tone if tone in VALID_TONES else DEFAULT_TONE
        sample = self._job_transcript_sample(job, transcript)
        suggestions = await asyncio.to_thread(
            generate_title_suggestions,
            sample,
            self._job_title_metadata(job),
            self.cfg,
            tone=normalized_tone,
        )
        TITLE_SUGGESTIONS_TOTAL.labels(status="ok").inc()
        return TitleSuggestionsResponse(
            job_id=job_id,
            tone=normalized_tone,
            suggestions=[
                TitleSuggestionOut(
                    rank=s.rank,
                    title=s.title,
                    confidence=min(1.0, max(0.0, s.confidence)),
                    hook=s.hook,
                )
                for s in suggestions
            ],
            model=self.cfg.llm.model,
            generated_at=datetime.now(timezone.utc),
        )

    async def to_dto(self, job: Job, *, title_audit_id: str | None = None) -> JobOut:
        """Convert ORM Job (with clips loaded) to JobOut with presigned URLs."""
        clip_dtos: list[ClipOut] = []
        for clip in job.clips:
            dto = ClipOut.model_validate(clip)
            if clip.final_storage_key:
                dto.download_url = self.storage.presigned_get_url(
                    clip.final_storage_key,
                    expires_in=self.cfg.storage.presigned_expiry_secs,
                )
            if clip.thumbnail_storage_key:
                dto.thumbnail_url = self.storage.presigned_get_url(
                    clip.thumbnail_storage_key,
                    expires_in=self.cfg.storage.presigned_expiry_secs,
                )
            dto.overlays = [
                ClipOverlayOut.model_validate(ov) for ov in clip.overlays
            ]
            publish_rows = PublishJobRepository.latest_per_platform(
                await self.publish_jobs.list_for_clip(clip.id),
            )
            dto.publish_statuses = [
                ClipPublishStatusOut(
                    platform=pj.platform,
                    status=pj.status,
                    publish_job_id=pj.id,
                    external_url=pj.external_url,
                )
                for pj in publish_rows
            ]
            clip_dtos.append(dto)

        snapshot_fields = {"clips", "content_profile", "aspect_ratio"}
        return JobOut(
            **{
                k: getattr(job, k)
                for k in JobOut.model_fields
                if k not in snapshot_fields and hasattr(job, k)
            },
            content_profile=(job.config_snapshot or {}).get("content_profile"),
            aspect_ratio=(job.config_snapshot or {}).get("aspect_ratio"),
            clips=clip_dtos,
            title_audit_id=title_audit_id,
        )

    async def regenerate_clip(
        self,
        job_id: str,
        clip_id: str,
        *,
        scope: RequestScope,
    ) -> str:
        job = await self.get_job(job_id, scope=scope)
        clip = next((c for c in job.clips if c.id == clip_id), None)
        if clip is None:
            exc = StreamClipError(
                f"Clip {clip_id} not found",
                user_message="Clip not found",
            )
            exc.code = "clip_not_found"
            exc.http_status = 404
            raise exc
        if clip.status != ClipStatus.DONE:
            exc = StreamClipError(
                "Clip is not finished rendering",
                user_message="Wait until this clip finishes before re-rendering.",
            )
            exc.code = "clip_not_ready"
            exc.http_status = 409
            raise exc
        await self.clips.reset_for_regenerate(clip_id)
        return clip_id

    async def update_clip(
        self,
        job_id: str,
        clip_id: str,
        body: UpdateClipRequest,
        *,
        scope: RequestScope,
    ) -> Clip:
        job = await self.get_job(job_id, scope=scope)
        clip = next((c for c in job.clips if c.id == clip_id), None)
        if clip is None:
            exc = StreamClipError("Clip not found", user_message="Clip not found")
            exc.code = "clip_not_found"
            exc.http_status = 404
            raise exc

        overrides: dict[str, object] = dict(clip.render_overrides or {})
        if body.caption_style is not None:
            overrides["caption_style"] = body.caption_style
        if body.reframe_preset is not None:
            overrides["reframe_preset"] = body.reframe_preset
        if body.aspect_ratio is not None:
            overrides["aspect_ratio"] = body.aspect_ratio
        if body.overlay_enabled is not None:
            overrides["overlay_enabled"] = body.overlay_enabled
        if body.transcript_edits is not None:
            if body.transcript_edits:
                overrides["transcript_edits"] = body.transcript_edits
            else:
                overrides.pop("transcript_edits", None)
        if body.caption_words_per_group is not None:
            overrides["caption_words_per_group"] = body.caption_words_per_group

        start = body.start_secs if body.start_secs is not None else clip.start_secs
        end = body.end_secs if body.end_secs is not None else clip.end_secs
        if end <= start:
            raise StreamClipError(
                "end_secs must be greater than start_secs",
                user_message="Clip end must be after start.",
            )
        if clip.status == ClipStatus.PROCESSING:
            raise StreamClipError(
                "Clip is currently rendering",
                user_message="Wait until this clip finishes before editing.",
            )

        title = body.title.strip() if body.title is not None else None
        hook = body.hook if body.hook is not None else None

        await self.clips.update_boundaries(
            clip_id,
            start_secs=start,
            end_secs=end,
            title=title,
            hook=hook,
            render_overrides=overrides,
        )
        if body.rerender and clip.status == ClipStatus.DONE:
            await self.clips.reset_for_regenerate(clip_id)
        await self.db.flush()
        updated = await self.clips.get(clip_id)
        if updated is None:
            raise StreamClipError("Clip not found")
        return updated

    async def get_clip_words(
        self,
        job_id: str,
        clip_id: str,
        *,
        scope: RequestScope,
    ) -> ClipWordsOut:
        """
        Caption word list for a clip window — the index basis for
        ``transcript_edits``. Mirrors the collection parameters used by
        the caption renderer so indices line up exactly.
        """
        job = await self.get_job(job_id, scope=scope)
        clip = next((c for c in job.clips if c.id == clip_id), None)
        if clip is None:
            exc = StreamClipError("Clip not found", user_message="Clip not found")
            exc.code = "clip_not_found"
            exc.http_status = 404
            raise exc

        try:
            transcript = await asyncio.to_thread(
                load_persisted_job_transcript, job_id, self.cfg, self.storage,
            )
        except FileNotFoundError:
            exc = StreamClipError(
                "Transcript not available",
                user_message="Transcript is not ready yet — wait for transcription to finish.",
            )
            exc.code = "transcript_not_ready"
            exc.http_status = 404
            raise exc from None

        min_prob = max(
            self.cfg.caption.min_word_probability,
            self.cfg.whisper.min_word_probability,
        )
        words = collect_words_for_window(
            transcript,
            clip.start_secs,
            clip.end_secs,
            rebase_to=0.0,
            min_probability=min_prob,
        )
        return ClipWordsOut(
            clip_id=clip_id,
            words=[
                ClipWordOut(index=i, text=w.text, start=w.start, end=w.end)
                for i, w in enumerate(words)
            ],
        )

    async def _load_job_transcript(self, job_id: str):
        try:
            return await asyncio.to_thread(
                load_persisted_job_transcript, job_id, self.cfg, self.storage,
            )
        except FileNotFoundError:
            exc = StreamClipError(
                "Transcript not available",
                user_message="Transcript is not ready yet — wait for transcription to finish.",
            )
            exc.code = "transcript_not_ready"
            exc.http_status = 404
            raise exc from None

    async def get_job_transcript_timestamps(
        self,
        job_id: str,
        *,
        scope: RequestScope,
    ) -> TranscriptTimestampsOut:
        t0 = time.perf_counter()
        await self.get_job(job_id, scope=scope)
        transcript = await self._load_job_transcript(job_id)

        min_prob = max(
            self.cfg.caption.min_word_probability,
            self.cfg.whisper.min_word_probability,
        )
        words_out: list[TranscriptWordOut] = []
        idx = 0
        for seg in transcript.segments:
            for w in seg.words:
                if w.probability < min_prob:
                    continue
                words_out.append(
                    TranscriptWordOut(
                        index=idx,
                        text=w.text,
                        start=w.start,
                        end=w.end,
                        confidence=w.probability,
                    ),
                )
                idx += 1

        segments_out = [
            TranscriptSegmentSummaryOut(
                id=seg.id,
                text=seg.text,
                start=seg.start,
                end=seg.end,
                word_count=len(seg.words),
            )
            for seg in transcript.segments
        ]
        CAPTION_PREVIEW_SECONDS.observe(time.perf_counter() - t0)
        return TranscriptTimestampsOut(
            job_id=job_id,
            language=transcript.language,
            duration_secs=transcript.duration,
            words=words_out,
            segments=segments_out,
        )

    async def export_job_captions(
        self,
        job_id: str,
        body: CaptionExportRequest,
        *,
        scope: RequestScope,
    ) -> CaptionExportOut:
        job = await self.get_job(job_id, scope=scope)

        if body.style is not None and not is_valid_caption_style(body.style):
            raise StreamClipError(
                "Invalid caption style",
                user_message=f"Unknown caption style: {body.style}",
                code="invalid_caption_style",
                http_status=422,
            )

        window_start: float | None = None
        window_end: float | None = None
        clip = None
        if body.clip_id is not None:
            clip = next((c for c in job.clips if c.id == body.clip_id), None)
            if clip is None:
                exc = StreamClipError("Clip not found", user_message="Clip not found")
                exc.code = "clip_not_found"
                exc.http_status = 404
                raise exc
            window_start = clip.start_secs
            window_end = clip.end_secs

        if body.format == "mp4" and body.clip_id is None:
            raise StreamClipError(
                "clip_id required for MP4 caption export",
                user_message="Select a clip to export a captioned MP4.",
                code="clip_id_required",
                http_status=422,
            )

        transcript = await self._load_job_transcript(job_id)
        snapshot = job.config_snapshot or {}
        caption_style = body.style or snapshot.get("caption_style", self.cfg.caption.style)
        export_settings = self.cfg.model_copy(deep=True)
        export_settings.caption.style = caption_style

        workspace = self.cfg.workspace_dir / "jobs" / job_id / "exports"
        workspace.mkdir(parents=True, exist_ok=True)

        if body.format == "mp4":
            assert clip is not None and window_start is not None and window_end is not None
            local_source = get_job_source_path(self.cfg, job_id)
            if not local_source.exists() and job.source_storage_key:
                local_source.parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(
                    self.storage.download,
                    job.source_storage_key,
                    local_source,
                )
            if not local_source.exists():
                raise StreamClipError(
                    "Source video not available",
                    user_message="Source video is missing — cannot burn captions.",
                    code="source_not_found",
                    http_status=404,
                )

            clip_path = workspace / f"export_{body.clip_id}.mp4"
            out_path = workspace / f"captions_{body.clip_id}.mp4"
            duration = max(0.1, window_end - window_start)
            await asyncio.to_thread(
                extract_segment,
                local_source,
                clip_path,
                start_secs=window_start,
                duration_secs=duration,
                export_cfg=export_settings.export,
            )
            emotion = clip.emotion or "neutral"
            await asyncio.to_thread(
                generate_captions,
                clip_path,
                out_path,
                transcript,
                window_start,
                window_end,
                export_settings,
                emotion,
            )
            filename = f"captions_{body.clip_id}.mp4"
            storage_key = job_key(job_id, "exports", filename)
            await asyncio.to_thread(self.storage.upload, storage_key, out_path)
        else:
            min_prob = max(
                self.cfg.caption.min_word_probability,
                self.cfg.whisper.min_word_probability,
            )
            export_tx = build_export_transcript(
                transcript,
                window_start=window_start,
                window_end=window_end,
                word_level=body.word_level,
                words_per_group=export_settings.caption.words_per_group,
                max_chars_per_line=export_settings.caption.max_chars_per_line,
                min_probability=min_prob,
            )

            fmt: CaptionExportFormat = body.format  # type: ignore[assignment]
            filename = caption_export_filename(fmt, clip_id=body.clip_id)
            storage_key = job_key(job_id, "exports", filename)
            local_path = workspace / filename

            ass_content: str | None = None
            if fmt == "ass":
                ass_content = build_ass_for_clip_window(
                    transcript,
                    clip_start=window_start or 0.0,
                    clip_end=window_end if window_end is not None else transcript.duration,
                    cfg=export_settings,
                    style=caption_style,
                )

            await asyncio.to_thread(
                export_caption_file,
                export_tx,
                local_path,
                fmt,
                ass_content=ass_content,
            )
            await asyncio.to_thread(self.storage.upload, storage_key, local_path)

        expires_in = self.cfg.storage.presigned_expiry_secs
        download_url = self.storage.presigned_get_url(storage_key, expires_in=expires_in)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        CAPTION_EXPORT_TOTAL.labels(format=body.format, status="ready").inc()
        return CaptionExportOut(
            job_id=job_id,
            format=body.format,
            status="ready",
            download_url=download_url,
            expires_at=expires_at,
        )

    async def splice_clips(
        self,
        job_id: str,
        clip_ids: list[str],
        *,
        scope: RequestScope,
        transition: str = "cut",
    ) -> Clip:
        job = await self.get_job(job_id, scope=scope)
        selected = [c for c in job.clips if c.id in clip_ids and c.kind != "splice"]
        if len(selected) < 2:
            raise StreamClipError(
                "Need at least two finished clips to splice",
                user_message="Select two or more rendered clips.",
            )
        for c in selected:
            if c.status != ClipStatus.DONE or not c.final_storage_key:
                raise StreamClipError(
                    "All clips must be fully rendered before splicing",
                    user_message="Wait for clips to finish rendering.",
                )

        job_ar = (job.config_snapshot or {}).get("aspect_ratio", "9:16")
        effective_ars = {
            (c.render_overrides or {}).get("aspect_ratio", job_ar) for c in selected
        }
        if len(effective_ars) > 1:
            raise StreamClipError(
                "Cannot splice clips with different aspect ratios",
                user_message="All merged clips must share the same aspect ratio.",
            )

        rank = max((c.rank for c in job.clips), default=0) + 1
        splice_clip = await self.clips.create(
            job_id=job_id,
            rank=rank,
            start_secs=min(c.start_secs for c in selected),
            end_secs=max(c.end_secs for c in selected),
            title="Merged highlight",
            hook=" ".join(c.hook for c in selected if c.hook)[:500],
            emotion=selected[0].emotion,
            transcript_text=" ".join(c.transcript_text for c in selected if c.transcript_text),
            kind="splice",
            parent_clip_ids=[c.id for c in selected],
            status=ClipStatus.PENDING,
        )
        splice_clip.render_overrides = {"transition": transition}
        await self.db.flush()
        return splice_clip

    def build_clips_zip(self, job: Job) -> bytes:
        from core.export_bundle import build_job_clips_zip
        return build_job_clips_zip(job, self.storage)


# ─── Upload service ──────────────────────────────────────────────────────────

class UploadService:
    def __init__(self, cfg: Settings, storage: Storage) -> None:
        self.cfg = cfg
        self.storage = storage

    async def init_upload(
        self,
        request: UploadInitRequest,
        scope: RequestScope,
    ) -> UploadInitResponse:
        if request.size_bytes is not None and request.size_bytes > self.cfg.storage.max_upload_bytes:
            limit_gb = self.cfg.storage.max_upload_bytes / (1024 ** 3)
            raise StreamClipError(
                f"Upload exceeds {limit_gb:.0f} GB limit",
                user_message=f"File is too large. Maximum upload size is {limit_gb:.0f} GB.",
                code="upload_too_large",
                http_status=413,
            )

        upload_id = uuid.uuid4().hex
        owner = scope.user_id or scope.device_id or "anonymous"

        # Sanitise filename
        safe_name = "".join(
            c if c.isalnum() or c in "-_." else "_"
            for c in request.filename
        )[:200]

        key = upload_key(owner, upload_id, safe_name)
        url = self.storage.presigned_put_url(
            key,
            expires_in=self.cfg.storage.presigned_expiry_secs,
            content_type=request.content_type,
        )
        return UploadInitResponse(
            upload_id=upload_id,
            upload_url=url,
            storage_key=key,
            expires_in=self.cfg.storage.presigned_expiry_secs,
        )
