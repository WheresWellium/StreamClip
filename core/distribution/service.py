"""Distribution publish orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ApprovalStatus, Clip, Job, VaultClip, VaultClipStatus
from backend.db.repositories import (
    ClipRepository,
    JobRepository,
    PlatformConnectionRepository,
    PublishJobRepository,
    VaultClipRepository,
)
from core.config import Settings
from core.distribution.errors import (
    ClipNotApprovedError,
    ClipNotReadyError,
    DuplicateInFlightError,
    NoConnectionError,
    PlatformNotEnabledError,
    VideoTooLongError,
)
from core.distribution.notify import notify_publish_event
from core.distribution.registry import get_platform_meta, list_platforms
from core.errors import StreamClipError
from core.tasks.publish_tasks import publish_to_platform

IN_FLIGHT_STATUSES = frozenset({"pending", "scheduled", "publishing"})


class DistributionService:
    def __init__(self, db: AsyncSession, cfg: Settings) -> None:
        self.db = db
        self.cfg = cfg
        self.publish_repo = PublishJobRepository(db)
        self.conn_repo = PlatformConnectionRepository(db)
        self.clip_repo = ClipRepository(db)
        self.job_repo = JobRepository(db)
        self.vault_repo = VaultClipRepository(db)

    def _platform_enabled(self, platform: str) -> bool:
        return any(p.id == platform for p in list_platforms())

    async def publish_now(
        self,
        *,
        user_id: str,
        clip_id: str | None = None,
        vault_clip_id: str | None = None,
        platform: str,
        title: str | None = None,
        description: str | None = None,
        scheduled_at: datetime | None = None,
        idempotency_key: str | None = None,
    ):
        return await self._enqueue(
            user_id=user_id,
            clip_id=clip_id,
            vault_clip_id=vault_clip_id,
            platform=platform,
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            idempotency_key=idempotency_key,
        )

    async def _enqueue(
        self,
        *,
        user_id: str,
        clip_id: str | None,
        vault_clip_id: str | None,
        platform: str,
        title: str | None,
        description: str | None,
        scheduled_at: datetime | None,
        idempotency_key: str | None,
    ):
        if bool(clip_id) == bool(vault_clip_id):
            raise StreamClipError(
                "clip_id xor vault_clip_id required",
                user_message="Select a clip source to publish.",
                code="invalid_source",
            )

        if not self._platform_enabled(platform):
            raise PlatformNotEnabledError(platform)

        meta = get_platform_meta(platform)
        if meta is None:
            raise PlatformNotEnabledError(platform)

        storage_key, duration_secs, default_title, default_description, approval_ok = (
            await self._resolve_source(user_id, clip_id, vault_clip_id)
        )
        if not approval_ok:
            raise ClipNotApprovedError()
        if not storage_key:
            raise ClipNotReadyError()
        if duration_secs > meta.max_duration_secs:
            raise VideoTooLongError(meta.max_duration_secs)

        connection = await self.conn_repo.get_by_platform(user_id, platform)
        if connection is None or not connection.is_active:
            raise NoConnectionError(platform)

        in_flight = await self.publish_repo.get_in_flight(
            clip_id=clip_id,
            vault_clip_id=vault_clip_id,
            platform=platform,
        )
        if in_flight is not None:
            raise DuplicateInFlightError(in_flight.id)

        if idempotency_key:
            existing = await self.publish_repo.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                owned = await self.publish_repo.get_for_user(existing.id, user_id)
                if owned is None:
                    raise StreamClipError(
                        "Idempotency key conflict",
                        user_message="This idempotency key is already in use.",
                        http_status=409,
                        code="idempotency_conflict",
                    )
                return existing

        now = datetime.now(timezone.utc)
        schedule = scheduled_at
        if schedule is not None and schedule.tzinfo is None:
            schedule = schedule.replace(tzinfo=timezone.utc)

        if schedule is not None and schedule > now:
            status = "scheduled"
        else:
            status = "pending"
            schedule = None

        job = await self.publish_repo.create(
            clip_id=clip_id,
            vault_clip_id=vault_clip_id,
            connection_id=connection.id,
            platform=platform,
            status=status,
            scheduled_at=schedule,
            title=(title or default_title or "")[: meta.title_max],
            description=description or default_description or "",
            idempotency_key=idempotency_key,
        )
        await self.db.flush()

        if status == "pending":
            publish_to_platform.delay(job.id)
        elif status == "scheduled":
            await notify_publish_event(self.db, job, event="publish.scheduled", cfg=self.cfg)

        return job

    async def _resolve_source(
        self,
        user_id: str,
        clip_id: str | None,
        vault_clip_id: str | None,
    ) -> tuple[str | None, float, str, str, bool]:
        if clip_id:
            clip = await self.clip_repo.get(clip_id, with_overlays=False)
            if clip is None:
                raise StreamClipError("Clip not found", user_message="Clip not found", http_status=404)
            job = await self.job_repo.get(clip.job_id)
            if job is None or job.owner_id != user_id:
                raise StreamClipError("Clip not found", user_message="Clip not found", http_status=404)
            return (
                clip.final_storage_key,
                clip.duration_secs,
                clip.title,
                clip.hook,
                clip.approval_status == ApprovalStatus.APPROVED.value,
            )

        assert vault_clip_id is not None
        row = await self.vault_repo.get_for_user(vault_clip_id, user_id)
        if row is None:
            raise StreamClipError(
                "Vault clip not found",
                user_message="Vault clip not found.",
                http_status=404,
            )
        if row.status != VaultClipStatus.READY.value:
            raise ClipNotReadyError()
        approved = True
        if row.source_clip_id:
            source = await self.clip_repo.get(row.source_clip_id, with_overlays=False)
            if source is not None:
                approved = source.approval_status == ApprovalStatus.APPROVED.value
        return (
            row.storage_key,
            row.duration_secs,
            row.title,
            row.hook,
            approved,
        )

    async def verify_clip_in_job(self, job_id: str, clip_id: str, user_id: str) -> Clip:
        job = await self.job_repo.get(job_id)
        if job is None or job.owner_id != user_id:
            raise StreamClipError("Job not found", user_message="Job not found", http_status=404)
        clip = await self.clip_repo.get(clip_id, with_overlays=False)
        if clip is None or clip.job_id != job_id:
            raise StreamClipError("Clip not found", user_message="Clip not found", http_status=404)
        return clip
