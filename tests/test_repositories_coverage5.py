"""H2 hot-path coverage — cold query edges in backend/db/repositories.py."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from backend.db.models import (
    ApprovalStatus,
    Clip,
    JobStatus,
    UserTier,
    VaultClipStatus,
)
from backend.db.repositories import (
    BugReportRepository,
    ClipRepository,
    DeviceRepository,
    FeedbackAttachmentRepository,
    InstallLicenseRepository,
    JobRepository,
    JobTitleAuditRepository,
    PasswordResetRepository,
    PublishJobRepository,
    UserRepository,
    VaultClipRepository,
)
from backend.middleware.device_id import normalize_device_id
from core.config import get_settings


async def _user(db, tag: str = "h2"):
    return await UserRepository(db).create(
        email=f"{tag}-{datetime.now().timestamp()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )


async def _job(db, **fields):
    return await JobRepository(db).create(
        owner_id=fields.get("owner_id"),
        device_id=fields.get("device_id"),
        source_url=fields.get("source_url", "https://example.test/v"),
        status=fields.get("status", JobStatus.QUEUED),
        current_stage="q",
        progress=0.0,
        config_snapshot={},
    )


@pytest.mark.asyncio
async def test_job_get_missing_and_device_mismatch(db):
    jobs = JobRepository(db)
    devices = DeviceRepository(db)
    assert await jobs.get("missing-job-id") is None
    assert await jobs.get_for_scope("missing-job-id", owner_id=None, device_id="x") is None

    dev_a = normalize_device_id("dev-a-device-0001")
    await devices.get_or_create(dev_a)
    job = await _job(db, device_id=dev_a)
    assert await jobs.get_for_scope(job.id, owner_id=None, device_id="dev-b-other") is None


@pytest.mark.asyncio
async def test_job_get_for_scope_signed_in_reads_device_job(db):
    """Authenticated GET may open a device-scoped job from the same install."""
    jobs = JobRepository(db)
    devices = DeviceRepository(db)
    user = await _user(db, "device-job")
    dev = normalize_device_id("signed-in-device-0001")
    await devices.get_or_create(dev)
    job = await _job(db, owner_id=None, device_id=dev)

    assert await jobs.get_for_scope(job.id, owner_id=user.id, device_id=dev) is not None
    assert await jobs.get_for_scope(job.id, owner_id=user.id, device_id="other-device-0001") is None
    # Device cookie is the ACL for unowned desktop jobs — any signed-in session
    # on the same install may open them (pre-claim / create without token).
    assert await jobs.get_for_scope(job.id, owner_id="other-user", device_id=dev) is not None
    assert (
        await jobs.get_for_scope(
            job.id, owner_id="other-user", device_id="other-device-0001"
        )
        is None
    )


@pytest.mark.asyncio
async def test_clip_boundaries_hook_overrides_and_approval(db):
    job = await _job(db)
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0.0, end_secs=2.0)

    await clips.update_boundaries(
        clip.id,
        start_secs=1.0,
        end_secs=3.5,
        title="T",
        hook="cold open",
        render_overrides={"crop": "center"},
    )
    await clips.update_approval(clip.id, ApprovalStatus.APPROVED.value)
    refreshed = await clips.get(clip.id)
    assert refreshed is not None
    assert refreshed.hook == "cold open"
    assert refreshed.render_overrides["crop"] == "center"
    assert refreshed.approval_status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_user_preferences_and_password(db):
    users = UserRepository(db)
    user = await _user(db, "prefs")

    assert await users.get_user_preferences("missing") == {}
    assert await users.update_user_preferences("missing", {"a": 1}) == {}

    merged = await users.update_user_preferences(user.id, {"theme": "dark", "lang": "en"})
    assert merged["theme"] == "dark"
    assert (await users.get_user_preferences(user.id))["lang"] == "en"

    await users.wipe_user_preferences(user.id)
    assert await users.get_user_preferences(user.id) == {}

    await users.update_password(user.id, "hashed-new")
    refreshed = await users.get(user.id)
    assert refreshed is not None
    assert refreshed.hashed_password == "hashed-new"


@pytest.mark.asyncio
async def test_password_reset_delete_by_hash(db):
    user = await _user(db, "pw")
    resets = PasswordResetRepository(db)
    token = await resets.create(
        user_id=user.id,
        token_hash=f"hash-{datetime.now().timestamp()}",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    await resets.delete_by_hash(token.token_hash)
    assert await resets.get_valid_by_hash(token.token_hash) is None


@pytest.mark.asyncio
async def test_device_claim_dev_stale_device_fallback(db, monkeypatch):
    """Development-only: claim anonymous jobs bound to a different device id."""
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "environment", "development")

    devices = DeviceRepository(db)
    user = await _user(db, "devclaim")
    stale_id = normalize_device_id("stale-browser-device")
    await devices.get_or_create(stale_id)

    stale = await _job(db, device_id=stale_id)
    claimed = await devices.claim_for_user("fresh-device-id", user.id)
    assert claimed >= 1
    await db.refresh(stale)
    assert stale.owner_id == user.id


@pytest.mark.asyncio
async def test_install_license_legacy_ledger_backfill(db):
    """Backfill path: activated + machine_id but no seat row yet."""
    from backend.db.models import InstallLicense, InstallLicenseActivation

    repo = InstallLicenseRepository(db)
    lic = InstallLicense(
        license_key_hash=f"legacy-{datetime.now().timestamp()}",
        tier=UserTier.PRO,
        status="activated",
        machine_id="legacy-machine-1",
        activated_at=datetime.now(timezone.utc),
        activation_count=1,
    )
    db.add(lic)
    await db.flush()

    await repo.ensure_activation_ledger(lic)
    rows = await repo.list_activations(lic)
    assert len(rows) == 1
    assert rows[0].machine_id == "legacy-machine-1"

    # Pending-in-session guard: unflushed seat row must not double-insert.
    lic2 = InstallLicense(
        license_key_hash=f"pending-{datetime.now().timestamp()}",
        tier=UserTier.PRO,
        status="activated",
        machine_id="legacy-machine-2",
        activated_at=datetime.now(timezone.utc),
        activation_count=1,
    )
    db.add(lic2)
    await db.flush()
    db.add(
        InstallLicenseActivation(
            license_id=lic2.id,
            machine_id="legacy-machine-2",
            status="active",
            activated_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    await repo.ensure_activation_ledger(lic2)
    await db.flush()
    assert await repo.count_active_activations(lic2) == 1


@pytest.mark.asyncio
async def test_install_license_seat_ledger_and_release(db):
    repo = InstallLicenseRepository(db)
    lic = await repo.create_issued(
        license_key_hash=f"seat-{datetime.now().timestamp()}",
        tier=UserTier.PRO,
        order_id="ord-seat-1",
        customer_email="Buyer@Example.COM",
    )

    # ensure_activation_ledger no-ops until activated + machine bound
    await repo.ensure_activation_ledger(lic)
    assert await repo.count_active_activations(lic) == 0

    await repo.mark_activated(
        lic,
        machine_id="machine-seat-1",
        entitlement_jwt="jwt-1",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        count_activation=True,
    )
    assert lic.status == "activated"
    assert lic.activation_count >= 1

    by_machine = await repo.get_activated_by_machine_id("machine-seat-1")
    assert by_machine is not None
    assert by_machine.id == lic.id
    assert await repo.get_activated_by_machine_id("nope") is None

    listed = await repo.list_activations(lic)
    assert len(listed) == 1
    assert listed[0].machine_id == "machine-seat-1"

    # Idempotent link_user
    user = await _user(db, "liclink")
    await repo.link_user(lic, user.id)
    await repo.link_user(lic, user.id)
    assert lic.user_id == user.id

    released = await repo.release_activation(lic, "machine-seat-1")
    assert released is not None
    assert released.status == "released"
    assert await repo.release_activation(lic, "machine-seat-1") is None
    assert await repo.release_activation(lic, "never-bound") is None
    assert lic.status == "issued"
    assert lic.machine_id is None

    # Re-activate then revoke
    await repo.mark_activated(
        lic,
        machine_id="machine-seat-2",
        entitlement_jwt="jwt-2",
        expires_at=None,
        count_activation=True,
    )
    await repo.revoke(lic)
    assert lic.status == "revoked"


@pytest.mark.asyncio
async def test_bug_report_filters_metrics_and_resolution_note(db):
    repo = BugReportRepository(db)
    oncall_a = await _user(db, "oncall-a")
    oncall_b = await _user(db, "oncall-b")
    open_high = await repo.create(
        categories=["pipeline", "ui"],
        severity="high",
        message="High open ticket with enough characters for validation.",
        assigned_to=oncall_a.id,
        status="open",
    )
    await repo.create(
        categories=["ui"],
        severity="low",
        message="Resolved already so it should drop from open severity counts.",
        status="resolved",
    )
    await db.flush()

    by_sev = await repo.list_filtered(limit=20, severity="high")
    assert any(r.id == open_high.id for r in by_sev)

    by_assignee = await repo.list_filtered(limit=20, assigned_to=oncall_a.id)
    assert any(r.id == open_high.id for r in by_assignee)

    by_cat = await repo.list_filtered(limit=20, category="pipeline")
    assert any(r.id == open_high.id for r in by_cat)

    since = date.today() - timedelta(days=1)
    by_since = await repo.list_filtered(limit=20, since=since)
    assert any(r.id == open_high.id for r in by_since)

    counts = await repo.count_open_by_severity()
    assert counts.get("high", 0) >= 1

    ages = await repo.open_ticket_ages_seconds()
    assert any(row["severity"] == "high" for row in ages)

    updated = await repo.update_ticket(
        open_high,
        status="resolved",
        assigned_to=oncall_b.id,
        resolution_note="fixed in H2",
    )
    assert updated.status == "resolved"
    assert updated.assigned_to == oncall_b.id
    assert (updated.environment or {}).get("resolution_note") == "fixed in H2"


@pytest.mark.asyncio
async def test_feedback_attachment_edge_paths(db):
    users = UserRepository(db)
    user = await _user(db, "att")
    att_repo = FeedbackAttachmentRepository(db)
    bug_repo = BugReportRepository(db)

    assert await att_repo.get("missing-att") is None
    assert await att_repo.link_to_report([], report_id="r", user_id=user.id, device_id=None) == []

    pending = await att_repo.create_pending(
        user_id=user.id,
        device_id=None,
        storage_key="support/u/a1.txt",
        filename="a1.txt",
        content_type="text/plain",
        size_bytes=10,
    )
    report = await bug_repo.create(
        categories=["ui"],
        severity="medium",
        message="Attachment ownership and list_for_report coverage path.",
        user_id=user.id,
    )
    await db.flush()

    with pytest.raises(ValueError, match="not found"):
        await att_repo.link_to_report(
            [pending.id, "ghost-id"],
            report_id=report.id,
            user_id=user.id,
            device_id=None,
        )

    other = await _user(db, "att2")
    with pytest.raises(ValueError, match="not owned by this user"):
        await att_repo.link_to_report(
            [pending.id],
            report_id=report.id,
            user_id=other.id,
            device_id=None,
        )

    with pytest.raises(ValueError, match="user or device scope"):
        await att_repo.link_to_report(
            [pending.id],
            report_id=report.id,
            user_id=None,
            device_id=None,
        )

    linked = await att_repo.link_to_report(
        [pending.id],
        report_id=report.id,
        user_id=user.id,
        device_id=None,
    )
    assert linked[0].bug_report_id == report.id

    with pytest.raises(ValueError, match="already linked"):
        await att_repo.link_to_report(
            [pending.id],
            report_id=report.id,
            user_id=user.id,
            device_id=None,
        )

    listed = await att_repo.list_for_report(report.id)
    assert [row.id for row in listed] == [pending.id]


@pytest.mark.asyncio
async def test_job_title_audit_create(db):
    user = await _user(db, "title")
    job = await _job(db, owner_id=user.id)
    audits = JobTitleAuditRepository(db)
    row = await audits.create(
        job_id=job.id,
        previous_title="Old",
        new_title="New",
        user_id=user.id,
        source="user_edit",
    )
    assert row.id
    assert row.previous_title == "Old"
    assert row.new_title == "New"


@pytest.mark.asyncio
async def test_publish_get_for_user_null_refs_and_vault_merge(db):
    user = await _user(db, "pub")
    other = await _user(db, "pub2")
    jobs = JobRepository(db)
    clips = ClipRepository(db)
    vault = VaultClipRepository(db)
    pubs = PublishJobRepository(db)

    assert await pubs.get_for_user("missing-pub", user.id) is None

    job = await _job(db, owner_id=user.id)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0.0, end_secs=1.0)
    vc = await vault.create(
        user_id=user.id,
        title="vault",
        status=VaultClipStatus.READY.value,
        source_clip_id=clip.id,
        storage_key="vault/a.mp4",
        file_size_bytes=100,
    )

    orphan = await pubs.create(
        platform="youtube",
        status="pending",
        title="orphan",
        clip_id=None,
        vault_clip_id=None,
    )
    assert await pubs.get_for_user(orphan.id, user.id) is None

    # clip_id set but Clip row missing (FK normally prevents; force via session get)
    dangling_clip = await clips.create(job_id=job.id, rank=1, start_secs=1.0, end_secs=2.0)
    pub_clip = await pubs.create(
        platform="youtube",
        status="pending",
        title="clip-pub",
        clip_id=dangling_clip.id,
    )
    real_get = db.get

    async def _get_missing_clip(model, ident, **kwargs):
        if model is Clip and ident == dangling_clip.id:
            return None
        return await real_get(model, ident, **kwargs)

    db.get = _get_missing_clip  # type: ignore[method-assign]
    try:
        assert await pubs.get_for_user(pub_clip.id, user.id) is None
    finally:
        db.get = real_get  # type: ignore[method-assign]

    pub_vault = await pubs.create(
        platform="tiktok",
        status="pending",
        title="vault-pub",
        vault_clip_id=vc.id,
    )
    pub_owned = await pubs.create(
        platform="youtube",
        status="pending",
        title="owned-clip-pub",
        clip_id=clip.id,
    )
    merged = await pubs.list_for_user(user.id, limit=10)
    ids = {p.id for p in merged}
    assert pub_vault.id in ids
    assert pub_owned.id in ids
    assert await pubs.get_for_user(pub_vault.id, other.id) is None


@pytest.mark.asyncio
async def test_mark_activated_zero_count_fallback(db, monkeypatch):
    """Defensive branch when count query returns 0 despite an insert."""
    repo = InstallLicenseRepository(db)
    lic = await repo.create_issued(
        license_key_hash=f"zero-{datetime.now().timestamp()}",
        tier=UserTier.PRO,
    )
    real_execute = db.execute

    async def _execute(statement, *args, **kwargs):
        result = await real_execute(statement, *args, **kwargs)
        sql = str(statement).lower()
        if "count" in sql and "install_license_activations" in sql:

            class _Zero:
                def scalar_one(self):
                    return 0

            return _Zero()
        return result

    monkeypatch.setattr(db, "execute", _execute)
    out = await repo.mark_activated(
        lic,
        machine_id="machine-zero",
        entitlement_jwt="jwt",
        expires_at=None,
        count_activation=True,
    )
    assert out.activation_count == 1


@pytest.mark.asyncio
async def test_vault_bytes_and_file_size_update(db):
    user = await _user(db, "vault")
    vault = VaultClipRepository(db)
    row = await vault.create(
        user_id=user.id,
        title="sized",
        status="ready",
        storage_key="vault/sized.mp4",
        file_size_bytes=250,
    )
    assert await vault.bytes_for_user(user.id) >= 250

    await vault.update_status(
        row.id,
        status="ready",
        storage_key="vault/sized2.mp4",
        thumb_storage_key="vault/sized2.jpg",
        file_size_bytes=400,
    )
    await db.refresh(row)
    assert row.file_size_bytes == 400
    assert row.thumb_storage_key == "vault/sized2.jpg"
    assert await vault.bytes_for_user(user.id) >= 400
