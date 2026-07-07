"""Clip feedback → style weight learning."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.api.schemas import CreateJobRequest
from backend.db.models import UserTier
from backend.db.repositories import ClipRepository, UserRepository
from backend.middleware.scope import RequestScope
from backend.services.feedback_service import apply_clip_style_feedback
from backend.services.job_service import JobService
from core.config import get_settings
from core.storage import LocalStorage

ANON = RequestScope(user_id=None, device_id="feedbackdevice01")


@pytest.mark.asyncio
async def test_apply_clip_style_feedback_updates_weights(db, tmp_path):
    cfg = get_settings(reload=True)
    users = UserRepository(db)
    user = await users.create(
        email="feedback@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    await db.flush()

    svc = JobService(db, cfg, LocalStorage(tmp_path))
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), ANON)
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        rank=0,
        start_secs=0,
        end_secs=5,
        audio_score=0.8,
        spectral_score=0.6,
        flow_score=0.4,
        chat_score=0.2,
        llm_score=70.0,
    )
    await db.flush()

    await apply_clip_style_feedback(db, clip=clip, user_id=user.id, rating=5)
    await db.flush()

    refreshed = await users.get(user.id)
    assert refreshed.style_weights


@pytest.mark.asyncio
async def test_apply_clip_style_feedback_unknown_user_noop(db, tmp_path):
    cfg = get_settings(reload=True)
    svc = JobService(db, cfg, LocalStorage(tmp_path))
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), ANON)
    clip = await ClipRepository(db).create(job_id=job.id, rank=0, start_secs=0, end_secs=1)
    await db.flush()
    await apply_clip_style_feedback(db, clip=clip, user_id="ghost", rating=3)
