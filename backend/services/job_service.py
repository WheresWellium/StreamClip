"""
StreamClip — Service Layer

Thin business-logic layer between API route handlers and the repositories.
The job creation flow lives here so it's reusable from REST routes, CLI
commands, and any future GraphQL or gRPC surface.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    ALLOWED_AUDIO_UPLOAD_TYPES,
    BatchCreateJobRequest,
    BatchCreateJobResponse,
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
    UpdateClipRequest,
    UpdateJobRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from backend.db.models import Clip, ClipStatus, Job, JobStatus
from backend.db.repositories import ClipRepository, DeviceRepository, JobRepository, PublishJobRepository, UserRepository
from backend.middleware.scope import RequestScope
from core.caption_timing import collect_words_for_window
from core.config import Settings
from core.billing import get_tier_limits
from core.errors import InvalidSourceError, JobNotFoundError, QuotaExceededError, StreamClipError
from core.storage import Storage, upload_key
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

        # Quota check
        if owner_id:
            user = await self.users.get(owner_id)
            if user and self.cfg.rate_limit.enabled:
                limits = get_tier_limits(user.tier)
                if user.jobs_used_this_month >= limits.max_jobs_per_month:
                    raise QuotaExceededError("Monthly job quota exceeded")
                if request.target_clips > limits.max_target_clips:
                    raise QuotaExceededError(
                        f"Your plan allows up to {limits.max_target_clips} clips per job",
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
        if job.celery_task_id:
            # Revoke the Celery task
            from core.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        await self.jobs.cancel(job_id)

    async def update_job(
        self,
        job_id: str,
        body: UpdateJobRequest,
        *,
        scope: RequestScope,
    ) -> Job:
        job = await self.jobs.get_for_scope(
            job_id,
            owner_id=scope.user_id,
            device_id=scope.device_id,
            device_scoped=self.cfg.auth.device_scoped_anonymous,
        )
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        updates = body.model_dump(exclude_unset=True)
        if "display_title" in updates:
            job.display_title = updates["display_title"]
            await self.db.flush()
        return await self.get_job(job_id, scope=scope)

    async def to_dto(self, job: Job) -> JobOut:
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
        if (
            request.content_type in ALLOWED_AUDIO_UPLOAD_TYPES
            and not self.cfg.features.audio_ingest
        ):
            raise StreamClipError(
                "Audio ingest is not enabled on this install",
                user_message="Audio uploads require the audio-to-clip add-on.",
                code="audio_ingest_disabled",
                http_status=403,
            )
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
