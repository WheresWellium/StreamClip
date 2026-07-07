"""Repository integration coverage for paths not in test_repositories_integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.db.models import (
    ApprovalStatus,
    ClipStatus,
    JobStatus,
    UserTier,
    VaultClipStatus,
)
from backend.middleware.device_id import normalize_device_id
from backend.db.repositories import (
    AssetRepository,
    ClipFeedbackRepository,
    ClipRepository,
    DeviceRepository,
    InstallLicenseRepository,
    JobRepository,
    JobTemplateRepository,
    PlatformConnectionRepository,
    PublishJobRepository,
    UserRepository,
    VaultClipRepository,
)
from core.config import get_settings
from core.distribution.tokens import encrypt_secret, generate_token_key


@pytest.fixture
def token_key():
    key = generate_token_key()
    cfg = get_settings(reload=True)
    old = cfg.distribution.token_encryption_key
    cfg.distribution.token_encryption_key = key
    yield key
    cfg.distribution.token_encryption_key = old


@pytest.mark.asyncio
async def test_job_template_repository(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"tpl{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    tpl_repo = JobTemplateRepository(db)
    tpl = await tpl_repo.create(user.id, "My preset", {"target_clips": 3})
    assert tpl.id
    listed = await tpl_repo.list_for_user(user.id)
    assert any(t.id == tpl.id for t in listed)
    got = await tpl_repo.get_for_user(tpl.id, user.id)
    assert got is not None
    assert await tpl_repo.delete(tpl.id, user.id) is True
    assert await tpl_repo.delete(tpl.id, user.id) is False


@pytest.mark.asyncio
async def test_clip_feedback_upsert(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"fb{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=None,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="q",
        progress=0.0,
        config_snapshot={},
    )
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0.0, end_secs=1.0)
    fb = ClipFeedbackRepository(db)
    first = await fb.upsert(clip.id, user_id=user.id, rating=5)
    second = await fb.upsert(clip.id, user_id=user.id, rating=2)
    assert first.id == second.id
    assert second.rating == 2


@pytest.mark.asyncio
async def test_device_repository_claim(db):
    devices = DeviceRepository(db)
    raw_device = "dev-claim-01"
    norm_device = normalize_device_id(raw_device)
    dev = await devices.get_or_create(raw_device)
    assert dev.id == norm_device
    await devices.mark_onboarding_complete(raw_device)
    await db.refresh(dev)
    assert dev.onboarding_complete is True

    users = UserRepository(db)
    user = await users.create(
        email=f"dev{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    job = await jobs.create(
        owner_id=None,
        device_id=norm_device,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="q",
        progress=0.0,
        config_snapshot={},
    )
    tagged = await devices.claim_for_user(raw_device, user.id)
    assert tagged >= 1
    await db.refresh(job)
    assert job.owner_id == user.id


@pytest.mark.asyncio
async def test_platform_connection_repository(db, token_key):
    users = UserRepository(db)
    user = await users.create(
        email=f"conn{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    conn_repo = PlatformConnectionRepository(db)
    created = await conn_repo.upsert_tokens(
        user_id=user.id,
        platform="youtube_shorts",
        account_label="Main",
        access_token_enc=encrypt_secret("tok1"),
        refresh_token_enc=encrypt_secret("ref1"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        metadata_json={"channel_id": "ch1"},
    )
    assert created.id
    updated = await conn_repo.upsert_tokens(
        user_id=user.id,
        platform="youtube_shorts",
        account_label="Main2",
        access_token_enc=encrypt_secret("tok2"),
        refresh_token_enc=None,
        token_expires_at=None,
    )
    assert updated.account_label == "Main2"
    by_platform = await conn_repo.get_by_platform(user.id, "youtube_shorts")
    assert by_platform is not None
    listed = await conn_repo.list_for_user(user.id)
    assert len(listed) == 1
    deactivated = await conn_repo.deactivate(created.id, user.id)
    assert deactivated is not None
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_publish_job_repository(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"pub{datetime.now().timestamp()}@test.local",
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
        job_id=job.id,
        rank=0,
        start_secs=0.0,
        end_secs=5.0,
        status=ClipStatus.DONE,
        final_storage_key="clips/f.mp4",
        approval_status=ApprovalStatus.APPROVED.value,
    )
    pub_repo = PublishJobRepository(db)
    pj = await pub_repo.create(
        clip_id=clip.id,
        platform="youtube_shorts",
        status="pending",
        title="T",
    )
    assert pj.id
    assert await pub_repo.get(pj.id) is not None
    assert await pub_repo.get_by_idempotency_key("missing") is None
    claimed = await pub_repo.claim_for_publish(pj.id)
    assert claimed is not None
    assert claimed.status == "publishing"
    released = await pub_repo.release_claim(pj.id)
    assert released is not None
    assert released.status == "pending"
    await pub_repo.mark_published(pj.id, external_id="ext", external_url="https://yt")
    await db.refresh(pj)
    assert pj.status == "published"

    pj2 = await pub_repo.create(
        clip_id=clip.id,
        platform="tiktok",
        status="failed",
        title="F",
        error_message="oops",
    )
    await pub_repo.mark_failed(pj2.id, message="fail", error_code="x")
    retried = await pub_repo.retry_failed(pj2.id)
    assert retried is not None

    listed = await pub_repo.list_for_user(user.id)
    assert len(listed) >= 1
    for_clip = await pub_repo.list_for_clip(clip.id)
    assert len(for_clip) >= 1
    latest = PublishJobRepository.latest_per_platform(for_clip)
    assert isinstance(latest, list)


@pytest.mark.asyncio
async def test_publish_job_scheduled_and_vault(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"sched{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    vault_repo = VaultClipRepository(db)
    vc = await vault_repo.create(
        user_id=user.id,
        title="Vault",
        status=VaultClipStatus.READY.value,
        storage_key="vault/v.mp4",
    )
    pub_repo = PublishJobRepository(db)
    due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    scheduled = await pub_repo.create(
        vault_clip_id=vc.id,
        platform="youtube_shorts",
        status="scheduled",
        scheduled_at=due_at,
        title="Scheduled",
    )
    due = await pub_repo.list_due_scheduled(limit=10)
    assert any(j.id == scheduled.id for j in due)
    promoted = await pub_repo.promote_scheduled_to_pending(scheduled.id)
    assert promoted is not None
    cancelled = await pub_repo.cancel(scheduled.id)
    assert cancelled is not None

    vault_jobs = await pub_repo.list_for_vault_clip(vc.id)
    assert len(vault_jobs) >= 1
    got = await pub_repo.get_for_user(scheduled.id, user.id)
    assert got is not None

    await vault_repo.rename(vc.id, user.id, "Renamed")
    await db.refresh(vc)
    assert vc.title == "Renamed"
    count = await vault_repo.count_for_user(user.id)
    assert count >= 1
    vault_list = await vault_repo.list_for_user(user.id)
    assert any(v.id == vc.id for v in vault_list)


@pytest.mark.asyncio
async def test_asset_repository_crud(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"asset{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    assets = AssetRepository(db)
    row = await assets.create(
        name="logo",
        asset_type="png",
        storage_key="assets/logo.png",
        description="brand",
        is_public=False,
        owner_id=user.id,
    )
    assert await assets.get(row.id) is not None
    mine = await assets.list_for_user(user.id)
    assert any(a.id == row.id for a in mine)
    await assets.delete(row.id)
    assert await assets.get(row.id) is None


@pytest.mark.asyncio
async def test_install_license_repository(db):
    lic_repo = InstallLicenseRepository(db)
    unique = f"hash-{datetime.now().timestamp()}"
    issued = await lic_repo.create_issued(
        license_key_hash=unique,
        order_id=f"ord-{datetime.now().timestamp()}",
        customer_email="buyer@test.local",
        tier=UserTier.PRO,
    )
    assert issued.status == "issued"
    by_hash = await lic_repo.get_by_key_hash(unique)
    assert by_hash is not None
    by_order = await lic_repo.get_by_order_id(issued.order_id)
    assert by_order is not None
    await lic_repo.get_active()
