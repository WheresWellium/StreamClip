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
from backend.db.models import ClipStatus
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


@pytest.mark.asyncio
async def test_password_reset_repository_create_and_lookup(db):
    import hashlib as _hashlib
    import secrets as _secrets
    from backend.db.repositories import PasswordResetRepository

    users = UserRepository(db)
    user = await users.create(
        email=f"reset{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    repo = PasswordResetRepository(db)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    raw = _secrets.token_hex(32)
    token_hash = _hashlib.sha256(raw.encode()).hexdigest()
    row = await repo.create(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires,
    )
    # get_valid_by_hash returns the row
    found = await repo.get_valid_by_hash(token_hash)
    assert found is not None
    assert found.id == row.id
    # expired hash returns None
    expired_hash = _hashlib.sha256(b"expired").hexdigest()
    await repo.create(
        user_id=user.id,
        token_hash=expired_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert await repo.get_valid_by_hash(expired_hash) is None


@pytest.mark.asyncio
async def test_password_reset_invalidate_deletes_user_tokens(db):
    from backend.db.repositories import PasswordResetRepository

    users = UserRepository(db)
    user = await users.create(
        email=f"inv{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    repo = PasswordResetRepository(db)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await repo.create(
        user_id=user.id,
        token_hash="b" * 64,
        expires_at=expires,
    )
    await repo.invalidate_for_user(user.id)
    row = await repo.get_valid_by_hash("b" * 64)
    assert row is None


@pytest.mark.asyncio
async def test_job_repo_scope_and_count(db):
    from backend.db.models import JobStatus
    users = UserRepository(db)
    jobs = JobRepository(db)
    user = await users.create(
        email=f"scope{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    j = await jobs.create(owner_id=user.id, status=JobStatus.QUEUED, source_url="https://t.tv/v/1")
    # get_for_scope — owner match
    assert await jobs.get_for_scope(j.id, owner_id=user.id) is not None
    # get_for_scope — wrong owner
    assert await jobs.get_for_scope(j.id, owner_id="wrong-id") is None
    # count_active
    count = await jobs.count_active()
    assert count >= 1
    # list_expired — j is not expired (created_at is now); expect empty or list
    expired = await jobs.list_expired(datetime.now(timezone.utc) - timedelta(hours=1))
    assert isinstance(expired, list)
    # cancel
    await jobs.cancel(j.id)
    cancelled = await jobs.get(j.id)
    assert cancelled.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_job_repo_list_for_scope_device_and_search(db):
    import secrets as _secrets
    from backend.db.models import JobStatus
    from backend.middleware.device_id import normalize_device_id
    devices = DeviceRepository(db)
    jobs = JobRepository(db)
    raw_dev = f"scope-dev-{_secrets.token_hex(4)}"
    dev = normalize_device_id(raw_dev)
    await devices.upsert(dev)
    await db.flush()
    j = await jobs.create(
        owner_id=None, device_id=dev, status=JobStatus.DONE, source_url="https://x.com/v/unique-xyz",
        display_title="unique-xyz-title",
    )
    # device-scoped list
    listed = await jobs.list_for_scope(owner_id=None, device_id=dev)
    assert any(x.id == j.id for x in listed)
    # search filter
    found = await jobs.list_for_scope(owner_id=None, device_id=dev, search="unique-xyz-title")
    assert any(x.id == j.id for x in found)
    notfound = await jobs.list_for_scope(owner_id=None, device_id=dev, search="zzznomatch")
    assert not any(x.id == j.id for x in notfound)
    # status filter
    done_list = await jobs.list_for_scope(owner_id=None, device_id=dev, status=JobStatus.DONE)
    assert any(x.id == j.id for x in done_list)


@pytest.mark.asyncio
async def test_job_repo_delete(db):
    from backend.db.models import JobStatus
    users = UserRepository(db)
    jobs = JobRepository(db)
    user = await users.create(
        email=f"del{datetime.now().timestamp()}@test.local",
        hashed_password="x", tier=UserTier.FREE,
    )
    j = await jobs.create(owner_id=user.id, status=JobStatus.DONE, source_url="https://t.tv/v/del")
    await jobs.delete(j.id)
    await db.flush()
    assert await jobs.get(j.id) is None
    # delete non-existent — should not raise
    await jobs.delete("nonexistent-id")


@pytest.mark.asyncio
async def test_user_repo_profile_updates(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"profile{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    await users.update_display_name(user.id, "TestDisplayName")
    await users.update_style_weights(user.id, {"weight_audio_energy": 0.5})
    await users.increment_minutes_processed(user.id, 12.5)
    await users.update_webhook(user.id, webhook_url="https://hook.test/x", webhook_secret="s")
    u = await users.get(user.id)
    assert u.display_name == "TestDisplayName"
    assert u.style_weights == {"weight_audio_energy": 0.5}
    assert u.minutes_processed_this_month >= 12.5
    assert u.webhook_url == "https://hook.test/x"
    # update_display_name for non-existent — should not raise
    await users.update_display_name("nonexistent", "X")


@pytest.mark.asyncio
async def test_license_link_by_email(db):
    lic_repo = InstallLicenseRepository(db)
    email = f"link{datetime.now().timestamp()}@test.local"
    users = UserRepository(db)
    user = await users.create(email=email, hashed_password="x", tier=UserTier.FREE)
    issued = await lic_repo.create_issued(
        license_key_hash=f"lhash-{datetime.now().timestamp()}",
        order_id=f"lord-{datetime.now().timestamp()}",
        customer_email=email,
        tier=UserTier.PRO,
    )
    count = await lic_repo.link_by_email(email, user.id)
    assert count == 1
    linked = await lic_repo.get(issued.id)
    assert linked.user_id == user.id
    # second call: already linked — count 0
    assert await lic_repo.link_by_email(email, user.id) == 0


@pytest.mark.asyncio
async def test_clip_repo_clear_overlays_and_reset(db):
    from backend.db.models import ClipStatus, JobStatus
    users = UserRepository(db)
    jobs = JobRepository(db)
    clips = ClipRepository(db)
    user = await users.create(
        email=f"clip{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    job = await jobs.create(owner_id=user.id, status=JobStatus.DONE, source_url="https://t.tv/v/c")
    clip = await clips.create(
        job_id=job.id,
        start_secs=0.0, end_secs=10.0, rank=1, ensemble_score=0.5,
        status=ClipStatus.DONE,
    )
    # add_overlay with valid fields
    await clips.add_overlay(clip.id, trigger_time_secs=0.5, duration_secs=3.0)
    c_with = await clips.get(clip.id, with_overlays=True)
    assert len(c_with.overlays) == 1
    # clear_overlays removes them
    await clips.clear_overlays(clip.id)
    # verify via direct query instead of ORM reload to avoid greenlet issue
    from sqlalchemy import select as _select
    from backend.db.models import ClipOverlay as _CO
    res = await db.execute(_select(_CO).where(_CO.clip_id == clip.id))
    assert list(res.scalars().all()) == []
    # reset_for_regenerate resets status
    await clips.reset_for_regenerate(clip.id)
    reset = await clips.get(clip.id)
    assert reset.status == ClipStatus.PENDING


@pytest.mark.asyncio
async def test_clip_repo_rerank_and_boundaries(db):
    from backend.db.models import ClipStatus, JobStatus
    users = UserRepository(db)
    jobs = JobRepository(db)
    clips = ClipRepository(db)
    user = await users.create(
        email=f"rerank{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    job = await jobs.create(owner_id=user.id, status=JobStatus.DONE, source_url="https://t.tv/v/r")
    c1 = await clips.create(job_id=job.id, start_secs=0.0, end_secs=5.0, rank=2, ensemble_score=0.3, status=ClipStatus.PENDING)
    c2 = await clips.create(job_id=job.id, start_secs=5.0, end_secs=10.0, rank=1, ensemble_score=0.8, status=ClipStatus.PENDING)
    await clips.rerank_by_ensemble(job.id)
    ranked = await clips.list_for_job(job.id)
    assert ranked[0].ensemble_score >= ranked[-1].ensemble_score
    # update_boundaries
    await clips.update_boundaries(c1.id, start_secs=1.0, end_secs=6.0)
    updated = await clips.get(c1.id)
    assert updated.start_secs == 1.0


@pytest.mark.asyncio
async def test_password_reset_mark_used(db):
    from backend.db.repositories import PasswordResetRepository
    from backend.services.auth_service import _hash_reset_token

    users = UserRepository(db)
    user = await users.create(
        email=f"used{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    repo = PasswordResetRepository(db)
    raw = "mark-used-token-value"
    row = await repo.create(
        user_id=user.id,
        token_hash=_hash_reset_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await repo.mark_used(row.id)
    assert await repo.get_valid_by_hash(_hash_reset_token(raw)) is None
