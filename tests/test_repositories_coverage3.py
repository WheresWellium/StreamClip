"""Repository integration tests for remaining uncovered branches."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.db.models import (
    ApprovalStatus,
    ClipStatus,
    JobStatus,
    UserTier,
    VaultClipStatus,
)
from backend.db.repositories import (
    ClipRepository,
    DeviceRepository,
    JobRepository,
    PublishJobRepository,
    UserRepository,
    VaultClipRepository,
)
from backend.middleware.device_id import normalize_device_id


@pytest.mark.asyncio
async def test_job_update_status_extended_fields(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"jobext{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=user.id,
        source_url="https://example.com/v.mp4",
        status=JobStatus.QUEUED,
    )
    started = datetime.now(timezone.utc)
    await jobs.update_status(
        job.id,
        JobStatus.INGESTING,
        stage="ingest",
        progress=1.5,
        error_code="E1",
        error_message="msg",
        pipeline_started_at=started,
        stage_durations_json={"ingest": 1.2},
    )
    await db.refresh(job)
    assert job.progress == 1.0
    assert job.pipeline_started_at == started
    assert job.stage_durations_json == {"ingest": 1.2}
    assert job.error_code == "E1"

    await jobs.update_status(job.id, JobStatus.PROCESSING)
    await db.refresh(job)
    assert job.started_at is not None

    await jobs.update_status(job.id, JobStatus.DONE)
    await db.refresh(job)
    assert job.finished_at is not None


@pytest.mark.asyncio
async def test_job_attach_celery_and_update_missing(db):
    jobs = JobRepository(db)
    await jobs.attach_celery_task("missing-job", "task-1")
    await jobs.update_status("missing-job", JobStatus.ERROR)


@pytest.mark.asyncio
async def test_user_webhook_and_style_weights(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"wh{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    await users.update_webhook(user.id, webhook_url="https://hook.test", webhook_secret="sec")
    await users.update_style_weights(user.id, {"hype": 0.9})
    await db.refresh(user)
    assert user.webhook_url == "https://hook.test"
    assert user.style_weights == {"hype": 0.9}
    await users.update_webhook("missing-user", webhook_url=None, webhook_secret=None)


@pytest.mark.asyncio
async def test_device_claim_legacy_null_jobs(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"dev{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    legacy = await jobs.create(
        owner_id=None,
        source_url="https://legacy.example/v.mp4",
        status=JobStatus.QUEUED,
    )
    assert legacy.device_id is None

    device_id = normalize_device_id("legacyclaim01")
    devices = DeviceRepository(db)
    tagged = await devices.claim_for_user(device_id, user.id)
    assert tagged >= 1
    await db.refresh(legacy)
    assert legacy.owner_id == user.id


@pytest.mark.asyncio
async def test_install_oauth_app_repository_upsert_mocked():
    from backend.db.models import InstallOAuthApp
    from backend.db.repositories import InstallOAuthAppRepository

    db = AsyncMock()
    existing = InstallOAuthApp(
        platform="youtube_shorts",
        client_id="old",
        client_secret_enc="enc",
        redirect_uri="http://localhost/cb",
    )
    db.get = AsyncMock(return_value=existing)
    db.add = MagicMock()
    db.flush = AsyncMock()

    repo = InstallOAuthAppRepository(db)
    updated = await repo.upsert(
        platform="youtube_shorts",
        client_id="new",
        client_secret_enc="enc2",
        redirect_uri="http://localhost/cb2",
    )
    assert updated.client_id == "new"

    db.get = AsyncMock(return_value=None)
    created = await repo.upsert(
        platform="tiktok",
        client_id="cid",
        client_secret_enc="enc",
        redirect_uri="http://localhost/t",
    )
    db.add.assert_called()
    assert created.platform == "tiktok"


@pytest.mark.asyncio
async def test_publish_repo_edge_paths(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"pubedge{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    jobs = JobRepository(db)
    job = await jobs.create(owner_id=user.id, source_url="https://x", status=JobStatus.DONE)
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        start_secs=0.0,
        end_secs=10.0,
        title="C",
        status=ClipStatus.DONE,
        final_storage_key="clips/f.mp4",
        approval_status=ApprovalStatus.APPROVED.value,
    )
    pub = PublishJobRepository(db)

    assert await pub.get_in_flight(clip_id=None, vault_clip_id=None, platform="youtube_shorts") is None

    pj = await pub.create(
        clip_id=clip.id,
        platform="youtube_shorts",
        status="pending",
        title="T",
    )
    await pub.mark_published("missing", external_id="x", external_url="y")
    await pub.mark_failed("missing", message="nope")

    other = await users.create(
        email=f"other{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    assert await pub.get_for_user(pj.id, other.id) is None

    unchanged = await pub.update_editable(pj.id)
    assert unchanged is not None
    assert unchanged.id == pj.id

    dup_platform = [
        await pub.create(clip_id=clip.id, platform="tiktok", status="failed", title="A"),
        await pub.create(clip_id=clip.id, platform="tiktok", status="failed", title="B"),
    ]
    latest = PublishJobRepository.latest_per_platform(dup_platform)
    assert len(latest) == 1


@pytest.mark.asyncio
async def test_clip_repo_overlays_and_approval(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"clipov{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    job = await jobs.create(owner_id=user.id, source_url="https://x", status=JobStatus.DONE)
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        start_secs=0.0,
        end_secs=5.0,
        title="O",
        status=ClipStatus.DONE,
    )
    await clips.add_overlay(clip.id, trigger_time_secs=0.0, duration_secs=1.0)
    await clips.clear_overlays(clip.id)
    await clips.update_boundaries("missing", start_secs=1.0)
    await clips.update_approval("missing", ApprovalStatus.APPROVED.value)
    await clips.reset_for_regenerate("missing")


@pytest.mark.asyncio
async def test_vault_repo_full_crud(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"vault{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    jobs = JobRepository(db)
    job = await jobs.create(owner_id=user.id, source_url="https://x", status=JobStatus.DONE)
    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        start_secs=0.0,
        end_secs=5.0,
        title="Src",
        status=ClipStatus.DONE,
        final_storage_key="clips/src.mp4",
    )
    vault = VaultClipRepository(db)
    row = await vault.create(
        user_id=user.id,
        title="V",
        status=VaultClipStatus.READY.value,
        storage_key="vault/v.mp4",
        source_clip_id=clip.id,
    )
    found = await vault.get_by_source_clip(user.id, clip.id)
    assert found is not None
    assert await vault.rename("missing", user.id, "X") is None
    await vault.update_status("missing", status="ready")
    assert await vault.delete("missing") is None
    deleted = await vault.delete(row.id)
    assert deleted is not None
