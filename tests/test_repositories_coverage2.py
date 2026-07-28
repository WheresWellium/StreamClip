"""PublishJobRepository and JobRepository search paths."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.db.models import ClipStatus, JobStatus, UserTier
from backend.db.repositories import (
    InstallLicenseRepository,
    JobRepository,
    PublishJobRepository,
)
from backend.db.repositories import PlatformConnectionRepository
from backend.db.repositories import UserRepository
from backend.db.repositories import ClipRepository


@pytest.mark.asyncio
async def test_job_list_for_scope_search(db):
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=None,
        source_url="https://unique-search-term.example/v",
        status=JobStatus.DONE,
        current_stage="done",
        progress=1.0,
        config_snapshot={},
        source_title="My Stream Title",
    )
    found = await jobs.list_for_scope(
        owner_id=None, device_id=None, device_scoped=False, search="unique-search",
    )
    assert any(j.id == job.id for j in found)
    empty = await jobs.list_for_scope(
        owner_id=None, device_id=None, device_scoped=False, search="zzz-no-match",
    )
    assert not any(j.id == job.id for j in empty)


@pytest.mark.asyncio
async def test_publish_get_in_flight_and_update_editable(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"pub2{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=user.id,
        source_url="https://x",
        status=JobStatus.DONE,
        current_stage="done",
        progress=1.0,
        config_snapshot={},
    )
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id, rank=0, start_secs=0.0, end_secs=5.0,
        status=ClipStatus.DONE, final_storage_key="k",
    )
    pub_repo = PublishJobRepository(db)
    pj = await pub_repo.create(
        clip_id=clip.id, platform="youtube_shorts", status="pending", title="Old",
    )
    in_flight = await pub_repo.get_in_flight(
        clip_id=clip.id, vault_clip_id=None, platform="youtube_shorts",
    )
    assert in_flight is not None
    assert await pub_repo.get_in_flight(
        clip_id=None, vault_clip_id=None, platform="youtube_shorts",
    ) is None

    updated = await pub_repo.update_editable(pj.id, title="New title", description="Desc")
    assert updated is not None
    assert updated.title == "New title"

    scheduled = await pub_repo.create(
        clip_id=clip.id,
        platform="tiktok",
        status="scheduled",
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
        title="Later",
    )
    rescheduled = await pub_repo.update_editable(
        scheduled.id, scheduled_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )
    assert rescheduled is not None


@pytest.mark.asyncio
async def test_publish_get_for_user_wrong_owner(db):
    users = UserRepository(db)
    owner = await users.create(
        email=f"own{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    other = await users.create(
        email=f"oth{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=owner.id,
        source_url="https://x",
        status=JobStatus.DONE,
        current_stage="done",
        progress=1.0,
        config_snapshot={},
    )
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0.0, end_secs=1.0)
    pub_repo = PublishJobRepository(db)
    pj = await pub_repo.create(clip_id=clip.id, platform="youtube_shorts", status="pending")
    assert await pub_repo.get_for_user(pj.id, owner.id) is not None
    assert await pub_repo.get_for_user(pj.id, other.id) is None


@pytest.mark.asyncio
async def test_install_license_mark_activated(db):
    lic_repo = InstallLicenseRepository(db)
    stamp = datetime.now().timestamp()
    lic = await lic_repo.create_issued(
        license_key_hash=f"h-{stamp}",
        tier=UserTier.PRO,
        order_id=f"o1-{stamp}",
    )
    out = await lic_repo.mark_activated(
        lic,
        machine_id=f"machine-cov2-{stamp}",
        entitlement_jwt="jwt",
        expires_at=None,
        count_activation=True,
    )
    assert out.status == "activated"
    assert out.activation_count >= 1


@pytest.mark.asyncio
async def test_platform_connection_deactivate_missing(db):
    repo = PlatformConnectionRepository(db)
    assert await repo.deactivate("missing-id", "user-1") is None
