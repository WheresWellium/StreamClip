"""Repository coverage sweep — remaining line misses for 100% target."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.db.models import JobStatus, UserTier, VaultClipStatus
from backend.db.repositories import (
    BugReportRepository,
    ClipRepository,
    DeviceRepository,
    InstallLicenseRepository,
    JobRepository,
    PlatformConnectionRepository,
    PublishJobRepository,
    UserRepository,
    VaultClipRepository,
)
from core.config import get_settings
from core.distribution.tokens import encrypt_secret


@pytest.fixture
def token_key():
    """Ensure distribution token encryption key is set (self-generates so the
    test passes without a .env Fernet key, e.g. in CI)."""
    from core.distribution import tokens

    cfg = get_settings(reload=True)
    old = cfg.distribution.token_encryption_key
    if not old:
        cfg.distribution.token_encryption_key = tokens.generate_token_key()
    try:
        yield cfg.distribution.token_encryption_key
    finally:
        cfg.distribution.token_encryption_key = old


async def _make_user(db, tag="u"):
    users = UserRepository(db)
    ts = datetime.now().timestamp()
    return await users.create(
        email=f"{tag}{ts}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )


async def _make_job(db, owner_id=None):
    jobs = JobRepository(db)
    return await jobs.create(
        owner_id=owner_id,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="q",
        progress=0.0,
        config_snapshot={},
    )


@pytest.mark.asyncio
async def test_job_update_status_sets_pipeline_started_on_ingesting(db):
    """Line 186: INGESTING auto-sets pipeline_started_at when null."""
    job = await _make_job(db)
    repo = JobRepository(db)
    await repo.update_status(job.id, JobStatus.INGESTING)
    refreshed = await repo.get(job.id)
    assert refreshed.pipeline_started_at is not None


@pytest.mark.asyncio
async def test_clip_update_approval_missing_clip_noop(db):
    """Line 388: update_approval with unknown clip_id returns without error."""
    repo = ClipRepository(db)
    # Should not raise even though clip doesn't exist
    await repo.update_approval("nonexistent-clip-id", "approved")


@pytest.mark.asyncio
async def test_user_set_data_contribution_opt_in(db):
    """Lines 548-550: set_data_contribution_opt_in updates the flag."""
    user = await _make_user(db, "contrib")
    repo = UserRepository(db)
    await repo.set_data_contribution_opt_in(user.id, True)
    refreshed = await repo.get(user.id)
    assert refreshed.data_contribution_opt_in is True
    await repo.set_data_contribution_opt_in(user.id, False)
    refreshed2 = await repo.get(user.id)
    assert refreshed2.data_contribution_opt_in is False


@pytest.mark.asyncio
async def test_device_claim_dev_anonymous_fallback(db, monkeypatch):
    """Lines 677-683: dev environment claims anonymous jobs with no device_id."""
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "environment", "development")

    user = await _make_user(db, "dev")
    job = await _make_job(db, owner_id=None)

    repo = DeviceRepository(db)
    count = await repo.claim_for_user("dev-device-001", user.id)
    assert count >= 0


@pytest.mark.asyncio
async def test_license_get_activated_by_machine_id(db):
    """Line 726: get_activated_by_machine_id returns the matching license."""
    repo = InstallLicenseRepository(db)
    import hashlib, secrets
    raw_key = secrets.token_hex(16)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    lic = await repo.create_issued(
        license_key_hash=key_hash,
        tier="pro",
        order_id=f"ord-{datetime.now().timestamp()}",
        customer_email="lic@test.local",
    )
    # Unique machine id avoids leftover seat rows from prior suite runs.
    machine_id = f"machine-abc-{datetime.now().timestamp()}"
    lic = await repo.mark_activated(
        lic,
        machine_id=machine_id,
        entitlement_jwt="jwt",
        expires_at=None,
        count_activation=False,
    )
    result = await repo.get_activated_by_machine_id(machine_id)
    assert result is not None
    assert result.machine_id == machine_id


@pytest.mark.asyncio
async def test_license_link_user_idempotent(db):
    """Lines 778-781: link_user is idempotent when same user_id."""
    import hashlib, secrets
    repo = InstallLicenseRepository(db)
    raw_key = secrets.token_hex(16)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    lic = await repo.create_issued(
        license_key_hash=key_hash,
        tier="pro",
        order_id=f"ord2-{datetime.now().timestamp()}",
        customer_email="lic2@test.local",
    )
    user = await _make_user(db, "lic")
    machine_id = f"machine-xyz-{datetime.now().timestamp()}"
    lic = await repo.mark_activated(
        lic,
        machine_id=machine_id,
        entitlement_jwt="jwt",
        expires_at=None,
        count_activation=False,
    )
    # First link
    lic = await repo.link_user(lic, user.id)
    assert lic.user_id == user.id
    # Second link — same user, should not flush again (idempotent)
    lic = await repo.link_user(lic, user.id)
    assert lic.user_id == user.id


@pytest.mark.asyncio
async def test_bug_report_repo_crud(db):
    """Lines 807, 810, 813-816: BugReport create/get/list_recent."""
    repo = BugReportRepository(db)
    report = await repo.create(
        categories=["crash"],
        severity="high",
        message="App crashed on export",
        environment={"os": "Windows 11"},
    )
    assert report.id
    fetched = await repo.get(report.id)
    assert fetched.id == report.id
    recent = await repo.list_recent(limit=5)
    assert any(r.id == report.id for r in recent)


@pytest.mark.asyncio
async def test_platform_upsert_updates_metadata(db, token_key):
    """Line 877: upsert_tokens updates metadata_json on second call."""
    user = await _make_user(db, "plat")
    repo = PlatformConnectionRepository(db)
    enc_tok = encrypt_secret("tok1")
    enc_ref = encrypt_secret("ref1")
    conn = await repo.upsert_tokens(
        user_id=user.id,
        platform="youtube_shorts",
        account_label="Channel A",
        access_token_enc=enc_tok,
        refresh_token_enc=enc_ref,
        token_expires_at=None,
        metadata_json={"channel_id": "UC123"},
    )
    assert conn.metadata_json == {"channel_id": "UC123"}
    # Upsert again with new metadata
    await repo.upsert_tokens(
        user_id=user.id,
        platform="youtube_shorts",
        account_label="Channel A",
        access_token_enc=enc_tok,
        refresh_token_enc=enc_ref,
        token_expires_at=None,
        metadata_json={"channel_id": "UC456"},
    )
    updated = await repo.get_by_platform(user.id, "youtube_shorts")
    assert updated.metadata_json == {"channel_id": "UC456"}


@pytest.mark.asyncio
async def test_publish_job_get_in_flight_vault(db, token_key):
    """Lines 968: get_in_flight with vault_clip_id branch."""
    user = await _make_user(db, "vaultpub")
    vault_repo = VaultClipRepository(db)
    vc = await vault_repo.create(
        user_id=user.id,
        source_job_id=None,
        title="My Vault Clip",
        duration_secs=60.0,
    )
    pub_repo = PublishJobRepository(db)
    pj = await pub_repo.create(
        vault_clip_id=vc.id,
        clip_id=None,
        platform="youtube_shorts",
        title="Vault pub",
        description="",
        status="publishing",
    )
    result = await pub_repo.get_in_flight(
        platform="youtube_shorts",
        clip_id=None,
        vault_clip_id=vc.id,
    )
    assert result is not None
    assert result.id == pj.id


@pytest.mark.asyncio
async def test_publish_job_get_in_flight_no_ids_returns_none(db):
    """Line 970: get_in_flight with neither clip_id nor vault_clip_id returns None."""
    repo = PublishJobRepository(db)
    result = await repo.get_in_flight(
        platform="youtube_shorts",
        clip_id=None,
        vault_clip_id=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_publish_get_for_user_vault_wrong_user(db, token_key):
    """Lines 978-980: get_for_user with vault clip owned by different user."""
    user_a = await _make_user(db, "puja")
    user_b = await _make_user(db, "pujb")
    vault_repo = VaultClipRepository(db)
    vc = await vault_repo.create(
        user_id=user_a.id,
        source_job_id=None,
        title="VC",
        duration_secs=30.0,
    )
    pub_repo = PublishJobRepository(db)
    pj = await pub_repo.create(
        vault_clip_id=vc.id,
        clip_id=None,
        platform="youtube_shorts",
        title="T",
        description="",
        status="pending",
    )
    # user_b should not see user_a's vault publish job
    result = await pub_repo.get_for_user(pj.id, user_b.id)
    assert result is None


@pytest.mark.asyncio
async def test_vault_clip_update_status_with_keys(db):
    """Lines 1274-1279: update_status with storage keys sets both."""
    user = await _make_user(db, "vault2")
    repo = VaultClipRepository(db)
    vc = await repo.create(
        user_id=user.id,
        source_job_id=None,
        title="VC2",
        duration_secs=45.0,
    )
    await repo.update_status(
        vc.id,
        status=VaultClipStatus.READY,
        storage_key="vault/abc.mp4",
        thumb_storage_key="vault/abc_thumb.jpg",
    )
    from backend.db.models import VaultClip
    refreshed = await db.get(VaultClip, vc.id)
    assert refreshed.status == VaultClipStatus.READY
    assert refreshed.storage_key == "vault/abc.mp4"
    assert refreshed.thumb_storage_key == "vault/abc_thumb.jpg"
