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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import (
    Asset,
    Clip,
    ClipOverlay,
    ClipStatus,
    Job,
    JobStatus,
    User,
)


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

    async def get_for_owner(self, job_id: str, owner_id: str | None) -> Job | None:
        job = await self.get(job_id)
        if job is None:
            return None
        if owner_id is not None:
            if job.owner_id != owner_id:
                return None
        elif job.owner_id is not None:
            return None
        return job

    async def list_for_owner(
        self,
        owner_id: str | None,
        *,
        limit: int = 50,
        offset: int = 0,
        status: JobStatus | None = None,
    ) -> list[Job]:
        stmt = (
            select(Job)
            .options(selectinload(Job.clips))
            .order_by(Job.created_at.desc())
        )
        if owner_id is not None:
            stmt = stmt.where(Job.owner_id == owner_id)
        else:
            stmt = stmt.where(Job.owner_id.is_(None))
        if status is not None:
            stmt = stmt.where(Job.status == status)
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
