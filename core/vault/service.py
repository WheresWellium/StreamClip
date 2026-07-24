"""Clip Vault business logic."""

from __future__ import annotations

from backend.db.models import ApprovalStatus, User, UserTier, VaultClip
from backend.db.repositories import ClipRepository, JobRepository, VaultClipRepository
from core.billing import get_tier_limits
from core.distribution.errors import (
    AlreadyInVaultError,
    ClipNotApprovedError,
    VaultFullError,
    VaultStorageFullError,
)
from core.errors import StreamClipError
from core.pipeline_metrics import VAULT_QUOTA_DENIED_TOTAL
from core.storage import make_storage
from core.config import Settings
from core.task_dispatch import dispatch_task_by_name
from sqlalchemy.ext.asyncio import AsyncSession


class VaultService:
    def __init__(self, db: AsyncSession, cfg: Settings) -> None:
        self.db = db
        self.cfg = cfg
        self.vault_repo = VaultClipRepository(db)
        self.clip_repo = ClipRepository(db)
        self.job_repo = JobRepository(db)
        self.storage = make_storage(cfg)

    async def _user_tier(self, user_id: str) -> UserTier:
        user = await self.db.get(User, user_id)
        return user.tier if user else UserTier.FREE

    async def save_clip_from_job(
        self,
        *,
        user_id: str,
        clip_id: str,
        title_override: str | None = None,
    ) -> VaultClip:
        clip = await self.clip_repo.get(clip_id, with_overlays=False)
        if clip is None or not clip.final_storage_key:
            raise StreamClipError(
                "Clip not ready",
                user_message="Clip must be fully rendered before saving to Vault.",
                code="clip_not_ready",
            )
        job = await self.job_repo.get(clip.job_id)
        if job is None or job.owner_id != user_id:
            raise StreamClipError(
                "Clip not found",
                user_message="Clip not found.",
                http_status=404,
            )
        if clip.approval_status != ApprovalStatus.APPROVED.value:
            raise ClipNotApprovedError()

        existing = await self.vault_repo.get_by_source_clip(user_id, clip_id)
        if existing is not None:
            raise AlreadyInVaultError()

        tier = await self._user_tier(user_id)
        limits = get_tier_limits(tier)
        count = await self.vault_repo.count_for_user(user_id)
        if count >= limits.max_vault_clips:
            VAULT_QUOTA_DENIED_TOTAL.labels(reason="clips").inc()
            raise VaultFullError(limits.max_vault_clips)

        used_bytes = await self.vault_repo.bytes_for_user(user_id)
        clip_bytes = int(getattr(clip, "file_size_bytes", 0) or 0)
        if clip_bytes > 0 and used_bytes + clip_bytes > limits.max_vault_bytes:
            VAULT_QUOTA_DENIED_TOTAL.labels(reason="bytes").inc()
            raise VaultStorageFullError(limits.max_vault_bytes)

        metadata = {
            "ensemble_score": clip.ensemble_score,
            "llm_score": clip.llm_score,
            "emotion": clip.emotion,
            "meme_keywords": clip.meme_keywords,
        }
        row = await self.vault_repo.create(
            user_id=user_id,
            source_clip_id=clip_id,
            source_job_id=clip.job_id,
            title=title_override or clip.title,
            hook=clip.hook,
            duration_secs=clip.duration_secs,
            status="copying",
            metadata_json=metadata,
        )
        await self.db.flush()

        # Dispatch by name — importing vault_tasks here would pull the heavy
        # pipeline task module into every API request path.
        dispatch_task_by_name(
            "core.tasks.vault_tasks.copy_clip_to_vault",
            args=(row.id, clip.final_storage_key, clip.thumbnail_storage_key),
        )
        return row

    def presigned_urls(self, row) -> tuple[str | None, str | None]:
        video = None
        thumb = None
        if row.storage_key and row.status == "ready":
            video = self.storage.presigned_get_url(
                row.storage_key,
                expires_in=self.cfg.storage.presigned_expiry_secs,
            )
        if row.thumb_storage_key and row.status == "ready":
            thumb = self.storage.presigned_get_url(
                row.thumb_storage_key,
                expires_in=self.cfg.storage.presigned_expiry_secs,
            )
        return video, thumb
