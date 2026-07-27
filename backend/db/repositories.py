"""
StreamClip — Repositories

Repository pattern: every query against the database goes through one of
these classes. Keeps SQL out of route handlers and Celery tasks, makes
testing easy (swap a repository for a fake), and centralises constraints
like "load clips ordered by rank" or "only return jobs for this owner".
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import String, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.middleware.device_id import normalize_device_id
from core.config import get_settings
from core.support.ticket_lifecycle import UNSET
from backend.db.models import (
    Asset,
    BugReport,
    Clip,
    ClipFeedback,
    ClipOverlay,
    ClipStatus,
    FeedbackAttachment,
    InstallLicense,
    Job,
    JobStatus,
    JobTemplate,
    JobTitleAudit,
    InstallOAuthApp,
    LocalDevice,
    PasswordResetToken,
    PlatformConnection,
    PublishJob,
    User,
    VaultClip,
)

IN_FLIGHT_PUBLISH_STATUSES = ("pending", "scheduled", "publishing")


# ─── Job repository ──────────────────────────────────────────────────────────

class JobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **fields: Any) -> Job:
        job = Job(**fields)
        self.db.add(job)
        await self.db.flush()
        return job

    async def get(self, job_id: str, *, with_clips: bool = False) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        if with_clips:
            stmt = stmt.options(
                selectinload(Job.clips).selectinload(Clip.overlays),
            )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_owner(
        self,
        job_id: str,
        owner_id: str | None,
        *,
        device_id: str | None = None,
        device_scoped: bool = True,
    ) -> Job | None:
        return await self.get_for_scope(
            job_id,
            owner_id=owner_id,
            device_id=device_id,
            device_scoped=device_scoped,
        )

    async def get_for_scope(
        self,
        job_id: str,
        *,
        owner_id: str | None,
        device_id: str | None = None,
        device_scoped: bool = True,
    ) -> Job | None:
        job = await self.get(job_id)
        if job is None:
            return None
        if owner_id is not None:
            return job if job.owner_id == owner_id else None
        if job.owner_id is not None:
            return None
        if device_scoped:
            if not device_id:
                return None
            return job if job.device_id == device_id else None
        return job

    async def list_for_owner(
        self,
        owner_id: str | None,
        *,
        device_id: str | None = None,
        device_scoped: bool = True,
        limit: int = 50,
        offset: int = 0,
        status: JobStatus | None = None,
        search: str | None = None,
    ) -> list[Job]:
        return await self.list_for_scope(
            owner_id=owner_id,
            device_id=device_id,
            device_scoped=device_scoped,
            limit=limit,
            offset=offset,
            status=status,
            search=search,
        )

    async def list_for_scope(
        self,
        *,
        owner_id: str | None,
        device_id: str | None = None,
        device_scoped: bool = True,
        limit: int = 50,
        offset: int = 0,
        status: JobStatus | None = None,
        search: str | None = None,
    ) -> list[Job]:
        stmt = (
            select(Job)
            .options(selectinload(Job.clips))
            .order_by(Job.created_at.desc())
        )
        if owner_id is not None:
            stmt = stmt.where(Job.owner_id == owner_id)
        elif device_scoped and device_id:
            stmt = stmt.where(Job.owner_id.is_(None), Job.device_id == device_id)
        else:
            stmt = stmt.where(Job.owner_id.is_(None))
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                (Job.display_title.ilike(pattern))
                | (Job.source_title.ilike(pattern))
                | (Job.source_url.ilike(pattern)),
            )
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        stage: str | None = None,
        progress: float | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        pipeline_started_at: datetime | None = None,
        stage_durations_json: dict[str, Any] | None = None,
    ) -> None:
        job = await self.get(job_id)
        if job is None:
            return
        job.status = status
        if stage is not None:
            job.current_stage = stage
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if error_code is not None:
            job.error_code = error_code
        if error_message is not None:
            job.error_message = error_message
        if pipeline_started_at is not None:
            job.pipeline_started_at = pipeline_started_at
        if stage_durations_json is not None:
            job.stage_durations_json = stage_durations_json
        if status == JobStatus.INGESTING and job.pipeline_started_at is None:
            job.pipeline_started_at = datetime.now(timezone.utc)
        if status == JobStatus.PROCESSING and job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        if status in (JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED):
            job.finished_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def attach_celery_task(self, job_id: str, task_id: str) -> None:
        job = await self.get(job_id)
        if job:
            job.celery_task_id = task_id
            await self.db.flush()

    async def cancel(self, job_id: str) -> None:
        await self.update_status(job_id, JobStatus.CANCELLED, stage="cancelled")

    async def delete(self, job_id: str) -> None:
        job = await self.get(job_id)
        if job:
            await self.db.delete(job)

    async def list_expired(
        self,
        before: datetime,
        *,
        limit: int = 100,
    ) -> list[Job]:
        terminal = (
            JobStatus.DONE,
            JobStatus.ERROR,
            JobStatus.CANCELLED,
        )
        stmt = (
            select(Job)
            .where(Job.created_at < before)
            .where(Job.status.in_(terminal))
            .order_by(Job.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        from sqlalchemy import func as sa_func

        active = (
            JobStatus.QUEUED,
            JobStatus.INGESTING,
            JobStatus.TRANSCRIBING,
            JobStatus.DETECTING,
            JobStatus.PROCESSING,
        )
        stmt = select(sa_func.count()).select_from(Job).where(Job.status.in_(active))
        result = await self.db.execute(stmt)
        return int(result.scalar_one())


# ─── Clip repository ─────────────────────────────────────────────────────────

class ClipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **fields: Any) -> Clip:
        clip = Clip(**fields)
        self.db.add(clip)
        await self.db.flush()
        return clip

    async def get(self, clip_id: str, *, with_overlays: bool = True) -> Clip | None:
        stmt = select(Clip).where(Clip.id == clip_id)
        if with_overlays:
            stmt = stmt.options(selectinload(Clip.overlays))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_job(self, job_id: str) -> list[Clip]:
        stmt = (
            select(Clip)
            .where(Clip.job_id == job_id)
            .order_by(Clip.rank.asc())
            .options(selectinload(Clip.overlays))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_storage_keys(
        self,
        clip_id: str,
        *,
        raw: str | None = None,
        vertical: str | None = None,
        captioned: str | None = None,
        final: str | None = None,
        thumbnail: str | None = None,
    ) -> None:
        clip = await self.get(clip_id, with_overlays=False)
        if clip is None:
            return
        if raw is not None: clip.raw_storage_key = raw
        if vertical is not None: clip.vertical_storage_key = vertical
        if captioned is not None: clip.captioned_storage_key = captioned
        if final is not None: clip.final_storage_key = final
        if thumbnail is not None: clip.thumbnail_storage_key = thumbnail
        await self.db.flush()

    async def mark_status(self, clip_id: str, status: ClipStatus,
                          *, error: str | None = None) -> None:
        clip = await self.get(clip_id, with_overlays=False)
        if clip is None:
            return
        clip.status = status
        if error is not None:
            clip.error_message = error
        await self.db.flush()

    async def update_virality(
        self,
        clip_id: str,
        *,
        llm_score: float,
        llm_reason: str,
        emotion: str,
        ensemble_score: float,
        meme_keywords: list[str] | None = None,
    ) -> None:
        clip = await self.get(clip_id, with_overlays=False)
        if clip is None:
            return
        clip.llm_score = llm_score
        clip.llm_reason = llm_reason
        clip.emotion = emotion
        clip.ensemble_score = ensemble_score
        if meme_keywords is not None:
            clip.meme_keywords = meme_keywords
        await self.db.flush()

    async def rerank_by_ensemble(self, job_id: str) -> None:
        """Re-assign rank 0..N-1 after virality updates."""
        clips = await self.list_for_job(job_id)
        ordered = sorted(clips, key=lambda c: c.ensemble_score, reverse=True)
        for rank, clip in enumerate(ordered):
            clip.rank = rank
        await self.db.flush()

    async def add_overlay(self, clip_id: str, **fields: Any) -> ClipOverlay:
        overlay = ClipOverlay(clip_id=clip_id, **fields)
        self.db.add(overlay)
        await self.db.flush()
        return overlay

    async def clear_overlays(self, clip_id: str) -> None:
        clip = await self.get(clip_id, with_overlays=True)
        if clip is None:
            return
        for ov in list(clip.overlays):
            await self.db.delete(ov)
        await self.db.flush()

    async def reset_for_regenerate(self, clip_id: str) -> None:
        """Mark clip pending and clear final artifact pointers for a forced re-render."""
        clip = await self.get(clip_id, with_overlays=False)
        if clip is None:
            return
        clip.status = ClipStatus.PENDING
        clip.error_message = None
        clip.final_storage_key = None
        clip.thumbnail_storage_key = None
        clip.render_time_secs = 0.0
        clip.file_size_bytes = 0
        await self.clear_overlays(clip_id)
        await self.db.flush()

    async def update_boundaries(
        self,
        clip_id: str,
        *,
        start_secs: float | None = None,
        end_secs: float | None = None,
        title: str | None = None,
        hook: str | None = None,
        render_overrides: dict[str, Any] | None = None,
    ) -> None:
        clip = await self.get(clip_id, with_overlays=False)
        if clip is None:
            return
        if start_secs is not None:
            clip.start_secs = start_secs
        if end_secs is not None:
            clip.end_secs = end_secs
        if title is not None:
            clip.title = title
        if hook is not None:
            clip.hook = hook
        if render_overrides is not None:
            merged = {**(clip.render_overrides or {}), **render_overrides}
            clip.render_overrides = merged
        await self.db.flush()

    async def update_approval(self, clip_id: str, approval_status: str) -> None:
        clip = await self.get(clip_id, with_overlays=False)
        if clip is None:
            return
        clip.approval_status = approval_status
        await self.db.flush()


# ─── Asset repository ────────────────────────────────────────────────────────

class AssetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_public(self) -> list[Asset]:
        result = await self.db.execute(
            select(Asset).where(Asset.is_public.is_(True)),
        )
        return list(result.scalars().all())

    async def list_for_user(self, user_id: str | None) -> list[Asset]:
        stmt = select(Asset).where(
            (Asset.is_public.is_(True)) | (Asset.owner_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def increment_use_count(self, asset_id: str) -> None:
        asset = await self.db.get(Asset, asset_id)
        if asset:
            asset.use_count += 1
            await self.db.flush()

    async def create(self, **fields: Any) -> Asset:
        asset = Asset(**fields)
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def get(self, asset_id: str) -> Asset | None:
        return await self.db.get(Asset, asset_id)

    async def delete(self, asset_id: str) -> None:
        asset = await self.get(asset_id)
        if asset:
            await self.db.delete(asset)
            await self.db.flush()


# ─── Job template repository ───────────────────────────────────────────────────

class JobTemplateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: str) -> list[JobTemplate]:
        result = await self.db.execute(
            select(JobTemplate)
            .where(JobTemplate.user_id == user_id)
            .order_by(JobTemplate.name.asc()),
        )
        return list(result.scalars().all())

    async def create(self, user_id: str, name: str, config_json: dict[str, Any]) -> JobTemplate:
        tpl = JobTemplate(user_id=user_id, name=name, config_json=config_json)
        self.db.add(tpl)
        await self.db.flush()
        return tpl

    async def get_for_user(self, template_id: str, user_id: str) -> JobTemplate | None:
        result = await self.db.execute(
            select(JobTemplate).where(
                JobTemplate.id == template_id,
                JobTemplate.user_id == user_id,
            ),
        )
        return result.scalar_one_or_none()

    async def delete(self, template_id: str, user_id: str) -> bool:
        tpl = await self.get_for_user(template_id, user_id)
        if tpl is None:
            return False
        await self.db.delete(tpl)
        await self.db.flush()
        return True


# ─── Clip feedback repository ──────────────────────────────────────────────────

class ClipFeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self,
        clip_id: str,
        user_id: str | None,
        rating: int,
    ) -> ClipFeedback:
        stmt = select(ClipFeedback).where(
            ClipFeedback.clip_id == clip_id,
            ClipFeedback.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.rating = rating
            await self.db.flush()
            return existing
        fb = ClipFeedback(clip_id=clip_id, user_id=user_id, rating=rating)
        self.db.add(fb)
        await self.db.flush()
        return fb


# ─── User repository ─────────────────────────────────────────────────────────

QUOTA_PERIOD_DAYS = 30


def roll_quota_period(user: User, *, now: datetime | None = None) -> bool:
    """Reset monthly counters when the user's quota period has lapsed.

    Counters are rolled lazily rather than by a scheduled task so desktop
    installs — which have no always-on scheduler — expire quotas exactly like
    the server profile. Returns True when a reset happened.
    """
    moment = now or datetime.now(timezone.utc)
    started = user.quota_period_start
    if started is None:
        user.quota_period_start = moment
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if (moment - started).days < QUOTA_PERIOD_DAYS:
        return False
    user.jobs_used_this_month = 0
    user.minutes_processed_this_month = 0.0
    user.quota_period_start = moment
    return True


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email),
        )
        return result.scalar_one_or_none()

    async def get(self, user_id: str) -> User | None:
        return await self.db.get(User, user_id)

    async def create(self, **fields: Any) -> User:
        user = User(**fields)
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_with_fresh_quota(self, user_id: str) -> User | None:
        """Load a user with monthly counters rolled over if the period lapsed."""
        user = await self.get(user_id)
        if user is not None:
            roll_quota_period(user)
        return user

    async def increment_jobs_used(self, user_id: str) -> None:
        user = await self.get(user_id)
        if user:
            roll_quota_period(user)
            user.jobs_used_this_month += 1
            await self.db.flush()

    async def increment_minutes_processed(self, user_id: str, minutes: float) -> None:
        user = await self.get(user_id)
        if user:
            roll_quota_period(user)
            user.minutes_processed_this_month += max(0.0, minutes)
            await self.db.flush()

    async def update_webhook(
        self,
        user_id: str,
        *,
        webhook_url: str | None,
        webhook_secret: str | None,
    ) -> None:
        user = await self.get(user_id)
        if user:
            user.webhook_url = webhook_url
            user.webhook_secret = webhook_secret
            await self.db.flush()

    async def set_data_contribution_opt_in(self, user_id: str, opted_in: bool) -> None:
        user = await self.get(user_id)
        if user:
            user.data_contribution_opt_in = opted_in
            await self.db.flush()

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        user = await self.get(user_id)
        if user is None:
            return {}
        return dict(user.user_preferences or {})

    async def update_user_preferences(
        self,
        user_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get(user_id)
        if user is None:
            return {}
        merged = {**(user.user_preferences or {}), **patch}
        user.user_preferences = merged
        await self.db.flush()
        return merged

    async def wipe_user_preferences(self, user_id: str) -> None:
        user = await self.get(user_id)
        if user:
            user.user_preferences = {}
            await self.db.flush()

    async def update_style_weights(self, user_id: str, weights: dict[str, Any]) -> None:
        user = await self.get(user_id)
        if user:
            user.style_weights = weights
            await self.db.flush()

    async def update_display_name(self, user_id: str, display_name: str) -> None:
        user = await self.get(user_id)
        if user:
            user.display_name = display_name
            await self.db.flush()

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        user = await self.get(user_id)
        if user:
            user.hashed_password = hashed_password
            await self.db.flush()


# ─── Password reset repository ───────────────────────────────────────────────

class PasswordResetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **fields: Any) -> PasswordResetToken:
        row = PasswordResetToken(**fields)
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            ),
        )
        return result.scalar_one_or_none()

    async def delete_by_hash(self, token_hash: str) -> None:
        """Remove any token with this hash (cross-user collision guard)."""
        from sqlalchemy import delete as _delete
        await self.db.execute(
            _delete(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash),
        )
        await self.db.flush()

    async def mark_used(self, token_id: str) -> None:
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc)),
        )
        await self.db.flush()

    async def invalidate_for_user(self, user_id: str) -> None:
        """Delete ALL reset tokens for this user (pending and used).

        The unique index on token_hash is unconditional — it covers used rows
        too. Keeping used rows would cause a UniqueViolationError when the same
        raw token is issued again (e.g. in tests, or if the hash space collides).
        Purging all past tokens on each new request is safe: the workflow is
        always generate → email → click → mark used, and an old used token is
        worthless anyway.
        """
        from sqlalchemy import delete as _delete
        await self.db.execute(
            _delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
            ),
        )
        await self.db.flush()


# ─── Device repository ───────────────────────────────────────────────────────

class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, device_id: str) -> LocalDevice:
        device_id = normalize_device_id(device_id)
        device = await self.db.get(LocalDevice, device_id)
        if device is None:
            device = LocalDevice(id=device_id)
            self.db.add(device)
            await self.db.flush()
        device.last_seen_at = datetime.now(timezone.utc)
        await self.db.flush()
        return device

    async def upsert(self, device_id: str) -> LocalDevice:
        return await self.get_or_create(device_id)

    async def mark_onboarding_complete(self, device_id: str) -> None:
        device = await self.get_or_create(device_id)
        device.onboarding_complete = True
        await self.db.flush()

    async def claim_for_user(self, device_id: str, user_id: str) -> int:
        device_id = normalize_device_id(device_id)
        device = await self.get_or_create(device_id)
        device.claimed_by_user_id = user_id

        tagged = await self.db.execute(
            update(Job)
            .where(Job.device_id == device_id, Job.owner_id.is_(None))
            .values(owner_id=user_id),
        )
        count = tagged.rowcount or 0

        # Jobs created before device_id wiring have owner_id=NULL, device_id=NULL.
        if count == 0:
            legacy = await self.db.execute(
                update(Job)
                .where(Job.owner_id.is_(None), Job.device_id.is_(None))
                .values(owner_id=user_id, device_id=device_id),
            )
            count = legacy.rowcount or 0

        # Local dev: recover anonymous jobs tied to a stale browser device id.
        if count == 0:
            if get_settings().environment == "development":
                dev_claim = await self.db.execute(
                    update(Job)
                    .where(Job.owner_id.is_(None))
                    .values(owner_id=user_id, device_id=device_id),
                )
                count = dev_claim.rowcount or 0

        await self.db.flush()
        return count


# ─── Install license repository ──────────────────────────────────────────────

class InstallLicenseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self) -> InstallLicense | None:
        result = await self.db.execute(
            select(InstallLicense)
            .where(InstallLicense.status == "activated")
            .order_by(InstallLicense.activated_at.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def get_by_key_hash(self, license_key_hash: str) -> InstallLicense | None:
        result = await self.db.execute(
            select(InstallLicense).where(InstallLicense.license_key_hash == license_key_hash),
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: str) -> InstallLicense | None:
        result = await self.db.execute(
            select(InstallLicense).where(InstallLicense.order_id == order_id).limit(1),
        )
        return result.scalar_one_or_none()

    async def get_activated_by_machine_id(self, machine_id: str) -> InstallLicense | None:
        result = await self.db.execute(
            select(InstallLicense)
            .where(
                InstallLicense.machine_id == machine_id,
                InstallLicense.status == "activated",
            )
            .order_by(InstallLicense.activated_at.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def create_issued(
        self,
        *,
        license_key_hash: str,
        tier,
        order_id: str | None = None,
        customer_email: str | None = None,
        capabilities: list[str] | None = None,
    ) -> InstallLicense:
        """Record a commerce-issued key that hasn't been activated yet."""
        lic = InstallLicense(
            license_key_hash=license_key_hash,
            tier=tier,
            order_id=order_id,
            customer_email=customer_email,
            capabilities=capabilities,
            status="issued",
        )
        self.db.add(lic)
        await self.db.flush()
        return lic

    async def mark_activated(
        self,
        lic: InstallLicense,
        *,
        machine_id: str,
        entitlement_jwt: str,
        expires_at: datetime | None,
        count_activation: bool,
    ) -> InstallLicense:
        lic.machine_id = machine_id
        lic.entitlement_jwt = entitlement_jwt
        lic.expires_at = expires_at
        lic.activated_at = datetime.now(timezone.utc)
        lic.status = "activated"
        if count_activation:
            lic.activation_count = (lic.activation_count or 0) + 1
        await self.db.flush()
        return lic

    async def get(self, license_id: str) -> InstallLicense | None:
        return await self.db.get(InstallLicense, license_id)

    async def revoke(self, lic: InstallLicense) -> InstallLicense:
        """Revoked rows are kept so re-activation of the key fails."""
        lic.status = "revoked"
        await self.db.flush()
        return lic

    async def link_user(self, lic: InstallLicense, user_id: str) -> InstallLicense:
        """Bind a license to its master user identity (idempotent)."""
        if lic.user_id != user_id:
            lic.user_id = user_id
            await self.db.flush()
        return lic

    async def link_by_email(self, email: str, user_id: str) -> int:
        """Link all unlinked licenses purchased with this email. Returns count."""
        result = await self.db.execute(
            select(InstallLicense).where(
                func.lower(InstallLicense.customer_email) == email.strip().lower(),
                InstallLicense.user_id.is_(None),
            ),
        )
        licenses = list(result.scalars().all())
        for lic in licenses:
            lic.user_id = user_id
        if licenses:
            await self.db.flush()
        return len(licenses)


class BugReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **fields: Any) -> BugReport:
        report = BugReport(**fields)
        self.db.add(report)
        await self.db.flush()
        return report

    async def get(self, report_id: str) -> BugReport | None:
        return await self.db.get(BugReport, report_id)

    async def list_recent(self, *, limit: int = 50) -> list[BugReport]:
        return await self.list_filtered(limit=limit)

    async def list_filtered(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
        severity: str | None = None,
        assigned_to: str | None = None,
        category: str | None = None,
        since: date | None = None,
    ) -> list[BugReport]:
        stmt = select(BugReport).order_by(BugReport.created_at.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(BugReport.status == status)
        if severity is not None:
            stmt = stmt.where(BugReport.severity == severity)
        if assigned_to is not None:
            stmt = stmt.where(BugReport.assigned_to == assigned_to)
        if category is not None:
            stmt = stmt.where(
                cast(BugReport.categories, String).like(f'%"{category}"%'),
            )
        if since is not None:
            since_dt = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
            stmt = stmt.where(BugReport.created_at >= since_dt)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_open_by_severity(self) -> dict[str, int]:
        stmt = (
            select(BugReport.severity, func.count())
            .where(BugReport.status != "resolved")
            .group_by(BugReport.severity)
        )
        result = await self.db.execute(stmt)
        return {severity: count for severity, count in result.all()}

    async def open_ticket_ages_seconds(self) -> list[dict[str, Any]]:
        stmt = select(BugReport.severity, BugReport.created_at).where(
            BugReport.status != "resolved",
        )
        result = await self.db.execute(stmt)
        return [
            {"severity": severity, "created_at": created_at}
            for severity, created_at in result.all()
        ]

    async def update_ticket(
        self,
        report: BugReport,
        *,
        status: str,
        assigned_to: str | None | object = UNSET,
        resolution_note: str | None = None,
    ) -> BugReport:
        report.status = status
        if assigned_to is not UNSET:
            report.assigned_to = assigned_to  # type: ignore[assignment]
        if resolution_note is not None:
            env = dict(report.environment or {})
            env["resolution_note"] = resolution_note
            report.environment = env
        await self.db.flush()
        return report


class FeedbackAttachmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_pending(
        self,
        *,
        user_id: str | None,
        device_id: str | None,
        storage_key: str,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> FeedbackAttachment:
        row = FeedbackAttachment(
            user_id=user_id,
            device_id=device_id,
            storage_key=storage_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get(self, attachment_id: str) -> FeedbackAttachment | None:
        return await self.db.get(FeedbackAttachment, attachment_id)

    async def link_to_report(
        self,
        attachment_ids: list[str],
        *,
        report_id: str,
        user_id: str | None,
        device_id: str | None,
    ) -> list[FeedbackAttachment]:
        if not attachment_ids:
            return []
        result = await self.db.execute(
            select(FeedbackAttachment).where(FeedbackAttachment.id.in_(attachment_ids)),
        )
        rows = list(result.scalars().all())
        if len(rows) != len(set(attachment_ids)):
            raise ValueError("One or more attachment ids were not found")
        for row in rows:
            if row.bug_report_id is not None:
                raise ValueError(f"Attachment {row.id} is already linked")
            if user_id is not None:
                if row.user_id != user_id:
                    raise ValueError(f"Attachment {row.id} is not owned by this user")
            elif device_id is not None:
                if row.device_id != device_id:
                    raise ValueError(f"Attachment {row.id} is not owned by this device")
            else:
                raise ValueError("Attachment ownership requires user or device scope")
            row.bug_report_id = report_id
        await self.db.flush()
        return rows

    async def list_for_report(self, report_id: str) -> list[FeedbackAttachment]:
        result = await self.db.execute(
            select(FeedbackAttachment).where(FeedbackAttachment.bug_report_id == report_id),
        )
        return list(result.scalars().all())


class JobTitleAuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        job_id: str,
        previous_title: str | None,
        new_title: str | None,
        user_id: str | None,
        source: str = "user_edit",
    ) -> JobTitleAudit:
        row = JobTitleAudit(
            job_id=job_id,
            previous_title=previous_title,
            new_title=new_title,
            user_id=user_id,
            source=source,
        )
        self.db.add(row)
        await self.db.flush()
        return row


# ─── Distribution repositories ───────────────────────────────────────────────

class PlatformConnectionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: str) -> list[PlatformConnection]:
        result = await self.db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user_id,
                PlatformConnection.is_active.is_(True),
            ),
        )
        return list(result.scalars().all())

    async def create(self, **fields: Any) -> PlatformConnection:
        conn = PlatformConnection(**fields)
        self.db.add(conn)
        await self.db.flush()
        return conn

    async def get_for_user(self, connection_id: str, user_id: str) -> PlatformConnection | None:
        result = await self.db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == connection_id,
                PlatformConnection.user_id == user_id,
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_platform(self, user_id: str, platform: str) -> PlatformConnection | None:
        result = await self.db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform,
                PlatformConnection.is_active.is_(True),
            ),
        )
        return result.scalar_one_or_none()

    async def upsert_tokens(
        self,
        *,
        user_id: str,
        platform: str,
        account_label: str,
        access_token_enc: str,
        refresh_token_enc: str | None,
        token_expires_at: datetime | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> PlatformConnection:
        existing = await self.get_by_platform(user_id, platform)
        if existing:
            existing.account_label = account_label
            existing.access_token_enc = access_token_enc
            existing.refresh_token_enc = refresh_token_enc
            existing.token_expires_at = token_expires_at
            if metadata_json is not None:
                existing.metadata_json = metadata_json
            existing.is_active = True
            await self.db.flush()
            return existing
        return await self.create(
            user_id=user_id,
            platform=platform,
            account_label=account_label,
            access_token_enc=access_token_enc,
            refresh_token_enc=refresh_token_enc,
            token_expires_at=token_expires_at,
            metadata_json=metadata_json or {},
            is_active=True,
        )

    async def deactivate(self, connection_id: str, user_id: str) -> PlatformConnection | None:
        conn = await self.get_for_user(connection_id, user_id)
        if conn is None:
            return None
        conn.is_active = False
        conn.access_token_enc = None
        conn.refresh_token_enc = None
        await self.db.flush()
        return conn


class InstallOAuthAppRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, platform: str) -> InstallOAuthApp | None:
        return await self.db.get(InstallOAuthApp, platform)

    async def upsert(
        self,
        *,
        platform: str,
        client_id: str,
        client_secret_enc: str,
        redirect_uri: str,
    ) -> InstallOAuthApp:
        row = await self.get(platform)
        if row is None:
            row = InstallOAuthApp(
                platform=platform,
                client_id=client_id,
                client_secret_enc=client_secret_enc,
                redirect_uri=redirect_uri,
            )
            self.db.add(row)
        else:
            row.client_id = client_id
            row.client_secret_enc = client_secret_enc
            row.redirect_uri = redirect_uri
        await self.db.flush()
        return row


class PublishJobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **fields: Any) -> PublishJob:
        job = PublishJob(**fields)
        self.db.add(job)
        await self.db.flush()
        return job

    async def get(self, publish_job_id: str) -> PublishJob | None:
        return await self.db.get(PublishJob, publish_job_id)

    async def get_by_idempotency_key(self, key: str) -> PublishJob | None:
        result = await self.db.execute(
            select(PublishJob).where(PublishJob.idempotency_key == key),
        )
        return result.scalar_one_or_none()

    async def get_in_flight(
        self,
        *,
        clip_id: str | None,
        vault_clip_id: str | None,
        platform: str,
    ) -> PublishJob | None:
        query = select(PublishJob).where(
            PublishJob.platform == platform,
            PublishJob.status.in_(tuple(IN_FLIGHT_PUBLISH_STATUSES)),
        )
        if clip_id:
            query = query.where(PublishJob.clip_id == clip_id)
        elif vault_clip_id:
            query = query.where(PublishJob.vault_clip_id == vault_clip_id)
        else:
            return None
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_for_user(self, publish_job_id: str, user_id: str) -> PublishJob | None:
        job = await self.get(publish_job_id)
        if job is None:
            return None
        if job.vault_clip_id:
            vc = await self.db.get(VaultClip, job.vault_clip_id)
            return job if vc and vc.user_id == user_id else None
        if job.clip_id:
            clip = await self.db.get(Clip, job.clip_id)
            if clip is None:
                return None
            parent = await self.db.get(Job, clip.job_id)
            return job if parent and parent.owner_id == user_id else None
        return None

    async def claim_for_publish(self, publish_job_id: str) -> PublishJob | None:
        result = await self.db.execute(
            update(PublishJob)
            .where(
                PublishJob.id == publish_job_id,
                PublishJob.status == "pending",
            )
            .values(
                status="publishing",
                attempt_count=PublishJob.attempt_count + 1,
            )
            .returning(PublishJob),
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.flush()
        return row

    async def mark_published(
        self,
        publish_job_id: str,
        *,
        external_id: str | None,
        external_url: str | None,
    ) -> None:
        job = await self.get(publish_job_id)
        if job is None:
            return
        job.status = "published"
        job.external_id = external_id
        job.external_url = external_url
        job.published_at = datetime.now(timezone.utc)
        job.error_message = None
        job.last_error_code = None
        await self.db.flush()

    async def release_claim(self, publish_job_id: str) -> PublishJob | None:
        """Return a claimed (publishing) job to pending so a retry can re-claim it."""
        result = await self.db.execute(
            update(PublishJob)
            .where(
                PublishJob.id == publish_job_id,
                PublishJob.status == "publishing",
            )
            .values(status="pending")
            .returning(PublishJob),
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.flush()
        return row

    async def mark_failed(
        self,
        publish_job_id: str,
        *,
        message: str,
        error_code: str | None = None,
    ) -> None:
        job = await self.get(publish_job_id)
        if job is None:
            return
        job.status = "failed"
        job.error_message = message
        job.last_error_code = error_code
        await self.db.flush()

    async def list_for_user(self, user_id: str, *, limit: int = 50) -> list[PublishJob]:
        clip_jobs = await self.db.execute(
            select(PublishJob)
            .join(Clip, PublishJob.clip_id == Clip.id)
            .join(Job, Clip.job_id == Job.id)
            .where(Job.owner_id == user_id)
            .order_by(PublishJob.created_at.desc())
            .limit(limit),
        )
        vault_jobs = await self.db.execute(
            select(PublishJob)
            .join(VaultClip, PublishJob.vault_clip_id == VaultClip.id)
            .where(VaultClip.user_id == user_id)
            .order_by(PublishJob.created_at.desc())
            .limit(limit),
        )
        merged = {j.id: j for j in clip_jobs.scalars().all()}
        for j in vault_jobs.scalars().all():
            merged.setdefault(j.id, j)
        return sorted(merged.values(), key=lambda j: j.created_at, reverse=True)[:limit]

    async def list_for_clip(self, clip_id: str) -> list[PublishJob]:
        result = await self.db.execute(
            select(PublishJob)
            .where(PublishJob.clip_id == clip_id)
            .order_by(PublishJob.created_at.desc()),
        )
        return list(result.scalars().all())

    async def list_for_vault_clip(self, vault_clip_id: str) -> list[PublishJob]:
        result = await self.db.execute(
            select(PublishJob)
            .where(PublishJob.vault_clip_id == vault_clip_id)
            .order_by(PublishJob.created_at.desc()),
        )
        return list(result.scalars().all())

    @staticmethod
    def latest_per_platform(jobs: list[PublishJob]) -> list[PublishJob]:
        seen: set[str] = set()
        latest: list[PublishJob] = []
        for job in jobs:
            if job.platform in seen:
                continue
            seen.add(job.platform)
            latest.append(job)
        return latest

    async def list_due_scheduled(
        self,
        *,
        before: datetime | None = None,
        limit: int = 50,
    ) -> list[PublishJob]:
        now = before or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(PublishJob)
            .where(
                PublishJob.status == "scheduled",
                PublishJob.scheduled_at <= now,
            )
            .order_by(PublishJob.scheduled_at.asc())
            .limit(limit),
        )
        return list(result.scalars().all())

    async def promote_scheduled_to_pending(self, publish_job_id: str) -> PublishJob | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(PublishJob)
            .where(
                PublishJob.id == publish_job_id,
                PublishJob.status == "scheduled",
                PublishJob.scheduled_at <= now,
            )
            .values(status="pending")
            .returning(PublishJob),
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.flush()
        return row

    async def cancel(self, publish_job_id: str) -> PublishJob | None:
        result = await self.db.execute(
            update(PublishJob)
            .where(
                PublishJob.id == publish_job_id,
                PublishJob.status.in_(("scheduled", "pending")),
            )
            .values(status="cancelled")
            .returning(PublishJob),
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.flush()
        return row

    async def update_editable(
        self,
        publish_job_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> PublishJob | None:
        """Edit metadata while the job hasn't started uploading yet."""
        values: dict[str, Any] = {}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if scheduled_at is not None:
            values["scheduled_at"] = scheduled_at
        if not values:
            return await self.get(publish_job_id)
        result = await self.db.execute(
            update(PublishJob)
            .where(
                PublishJob.id == publish_job_id,
                PublishJob.status.in_(("pending", "scheduled")),
            )
            .values(**values)
            .returning(PublishJob),
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.flush()
        return row

    async def retry_failed(self, publish_job_id: str) -> PublishJob | None:
        result = await self.db.execute(
            update(PublishJob)
            .where(
                PublishJob.id == publish_job_id,
                PublishJob.status == "failed",
            )
            .values(
                status="pending",
                error_message=None,
                last_error_code=None,
            )
            .returning(PublishJob),
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.flush()
        return row


class VaultClipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def count_for_user(self, user_id: str) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(VaultClip).where(
                VaultClip.user_id == user_id,
                VaultClip.status != "failed",
                VaultClip.archived_flag.is_(False),
            ),
        )
        return int(result.scalar_one())

    async def bytes_for_user(self, user_id: str) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.coalesce(func.sum(VaultClip.file_size_bytes), 0)).where(
                VaultClip.user_id == user_id,
                VaultClip.status != "failed",
                VaultClip.archived_flag.is_(False),
            ),
        )
        return int(result.scalar_one())

    async def get_for_user(self, vault_clip_id: str, user_id: str) -> VaultClip | None:
        result = await self.db.execute(
            select(VaultClip).where(
                VaultClip.id == vault_clip_id,
                VaultClip.user_id == user_id,
            ),
        )
        return result.scalar_one_or_none()

    async def rename(self, vault_clip_id: str, user_id: str, title: str) -> VaultClip | None:
        row = await self.get_for_user(vault_clip_id, user_id)
        if row is None:
            return None
        row.title = title
        await self.db.flush()
        return row

    async def get_by_source_clip(self, user_id: str, source_clip_id: str) -> VaultClip | None:
        result = await self.db.execute(
            select(VaultClip).where(
                VaultClip.user_id == user_id,
                VaultClip.source_clip_id == source_clip_id,
                VaultClip.status.in_(["copying", "ready"]),
            ),
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str, *, limit: int = 100) -> list[VaultClip]:
        result = await self.db.execute(
            select(VaultClip)
            .where(VaultClip.user_id == user_id)
            .order_by(VaultClip.saved_at.desc())
            .limit(limit),
        )
        return list(result.scalars().all())

    async def create(self, **fields: Any) -> VaultClip:
        row = VaultClip(**fields)
        self.db.add(row)
        await self.db.flush()
        return row

    async def update_status(
        self,
        vault_clip_id: str,
        *,
        status: str,
        storage_key: str | None = None,
        thumb_storage_key: str | None = None,
        file_size_bytes: int | None = None,
    ) -> None:
        row = await self.db.get(VaultClip, vault_clip_id)
        if row is None:
            return
        row.status = status
        if storage_key is not None:
            row.storage_key = storage_key
        if thumb_storage_key is not None:
            row.thumb_storage_key = thumb_storage_key
        if file_size_bytes is not None:
            row.file_size_bytes = file_size_bytes
        await self.db.flush()

    async def delete(self, vault_clip_id: str) -> VaultClip | None:
        row = await self.db.get(VaultClip, vault_clip_id)
        if row is None:
            return None
        await self.db.delete(row)
        await self.db.flush()
        return row


# Alias for license API
LicenseRepository = InstallLicenseRepository
