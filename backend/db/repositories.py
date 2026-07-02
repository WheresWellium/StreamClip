"""
StreamClip — Repositories

Repository pattern: every query against the database goes through one of
these classes. Keeps SQL out of route handlers and Celery tasks, makes
testing easy (swap a repository for a fake), and centralises constraints
like "load clips ordered by rank" or "only return jobs for this owner".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.middleware.device_id import normalize_device_id
from backend.db.models import (
    Asset,
    Clip,
    ClipFeedback,
    ClipOverlay,
    ClipStatus,
    InstallLicense,
    Job,
    JobStatus,
    JobTemplate,
    InstallOAuthApp,
    LocalDevice,
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
                (Job.source_title.ilike(pattern)) | (Job.source_url.ilike(pattern)),
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

    async def increment_jobs_used(self, user_id: str) -> None:
        user = await self.get(user_id)
        if user:
            user.jobs_used_this_month += 1
            await self.db.flush()

    async def increment_minutes_processed(self, user_id: str, minutes: float) -> None:
        user = await self.get(user_id)
        if user:
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

    async def update_style_weights(self, user_id: str, weights: dict[str, Any]) -> None:
        user = await self.get(user_id)
        if user:
            user.style_weights = weights
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

        await self.db.flush()
        return count


# ─── Install license repository ──────────────────────────────────────────────

class InstallLicenseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self) -> InstallLicense | None:
        result = await self.db.execute(
            select(InstallLicense).order_by(InstallLicense.activated_at.desc()).limit(1),
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        license_key_hash: str,
        machine_id: str,
        tier,
        entitlement_jwt: str,
        expires_at: datetime | None,
    ) -> InstallLicense:
        result = await self.db.execute(
            select(InstallLicense).where(InstallLicense.license_key_hash == license_key_hash),
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.machine_id = machine_id
            existing.tier = tier
            existing.entitlement_jwt = entitlement_jwt
            existing.expires_at = expires_at
            existing.activated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return existing
        lic = InstallLicense(
            license_key_hash=license_key_hash,
            machine_id=machine_id,
            tier=tier,
            entitlement_jwt=entitlement_jwt,
            expires_at=expires_at,
        )
        self.db.add(lic)
        await self.db.flush()
        return lic


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
    ) -> None:
        row = await self.db.get(VaultClip, vault_clip_id)
        if row is None:
            return
        row.status = status
        if storage_key is not None:
            row.storage_key = storage_key
        if thumb_storage_key is not None:
            row.thumb_storage_key = thumb_storage_key
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
