"""
StreamClip — Service Layer

Thin business-logic layer between API route handlers and the repositories.
The job creation flow lives here so it's reusable from REST routes, CLI
commands, and any future GraphQL or gRPC surface.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    ClipOut,
    ClipOverlayOut,
    CreateJobRequest,
    JobOut,
    UploadInitRequest,
    UploadInitResponse,
)
from backend.db.models import Clip, Job, JobStatus
from backend.db.repositories import ClipRepository, JobRepository, UserRepository
from core.config import Settings
from core.errors import InvalidSourceError, JobNotFoundError, QuotaExceededError
from core.storage import Storage, upload_key

log = structlog.get_logger(__name__)


# ─── Job service ─────────────────────────────────────────────────────────────

class JobService:
    def __init__(self, db: AsyncSession, cfg: Settings, storage: Storage) -> None:
        self.db = db
        self.cfg = cfg
        self.storage = storage
        self.jobs = JobRepository(db)
        self.clips = ClipRepository(db)
        self.users = UserRepository(db)

    async def create_job(
        self,
        request: CreateJobRequest,
        owner_id: str | None,
    ) -> Job:
        if not request.source_url and not request.source_upload_key:
            raise InvalidSourceError("Must provide source_url OR source_upload_key")

        # Quota check
        if owner_id:
            user = await self.users.get(owner_id)
            if user and self.cfg.rate_limit.enabled:
                if user.jobs_used_this_month >= self.cfg.rate_limit.jobs_per_hour * 24 * 30:
                    raise QuotaExceededError("Monthly job quota exceeded")

        # Snapshot the config the job will use. This freezes settings so
        # later config changes don't break repeatability.
        config_snapshot = {
            "target_clips": request.target_clips,
            "caption_style": request.caption_style,
            "reframe_preset": request.reframe_preset,
            "content_profile": request.content_profile,
            "whisper_model": self.cfg.whisper.model_size,
            "llm_provider": self.cfg.llm.provider,
            "llm_model": self.cfg.llm.model,
        }

        job = await self.jobs.create(
            owner_id=owner_id,
            source_url=request.source_url,
            source_storage_key=request.source_upload_key,
            config_snapshot=config_snapshot,
            status=JobStatus.QUEUED,
            current_stage="queued",
            progress=0.0,
        )
        if owner_id:
            await self.users.increment_jobs_used(owner_id)
        log.info("job_created", job_id=job.id, owner=owner_id)
        return job

    async def get_job(self, job_id: str, *, owner_id: str | None) -> Job:
        job = await self.jobs.get_for_owner(job_id, owner_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        # Eager-load clips
        return await self.jobs.get(job_id, with_clips=True)  # type: ignore[return-value]

    async def list_jobs(
        self,
        owner_id: str | None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        return await self.jobs.list_for_owner(owner_id, limit=limit, offset=offset)

    async def cancel_job(self, job_id: str, owner_id: str | None) -> None:
        job = await self.jobs.get_for_owner(job_id, owner_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        if job.celery_task_id:
            # Revoke the Celery task
            from core.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        await self.jobs.cancel(job_id)

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
            clip_dtos.append(dto)

        return JobOut(
            **{
                k: getattr(job, k)
                for k in JobOut.model_fields if k != "clips" and k != "content_profile" and hasattr(job, k)
            },
            content_profile=(job.config_snapshot or {}).get("content_profile"),
            clips=clip_dtos,
        )

    async def regenerate_clip(
        self,
        job_id: str,
        clip_id: str,
        *,
        owner_id: str | None,
    ) -> str:
        from backend.db.models import ClipStatus
        from core.errors import StreamClipError

        job = await self.get_job(job_id, owner_id=owner_id)
        clip = next((c for c in job.clips if c.id == clip_id), None)
        if clip is None:
            raise StreamClipError(
                f"Clip {clip_id} not found",
                code="clip_not_found",
                http_status=404,
            )
        if clip.status != ClipStatus.DONE:
            raise StreamClipError(
                "Clip is not finished rendering",
                code="clip_not_ready",
                user_message="Wait until this clip finishes before re-rendering.",
            )
        await self.clips.reset_for_regenerate(clip_id)
        return clip_id

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
        owner_id: str | None,
    ) -> UploadInitResponse:
        upload_id = uuid.uuid4().hex
        owner = owner_id or "anonymous"

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
