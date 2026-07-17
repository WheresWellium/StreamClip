"""Line-coverage sweep for backend services, repositories, middleware, db
session/models and static UI helpers (MASTER_TODO section 3.10 line pillar)."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.models import JobStatus, UserTier
from backend.db.repositories import (
    ClipRepository,
    DeviceRepository,
    InstallLicenseRepository,
    JobRepository,
    PublishJobRepository,
    UserRepository,
    VaultClipRepository,
)
from backend.services.auth_service import AuthService
from core.config import get_settings


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _make_user(db, tag="bc"):
    users = UserRepository(db)
    return await users.create(
        email=f"{tag}-{uuid.uuid4().hex[:10]}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )


async def _make_job(db, owner_id=None, device_id=None, **extra):
    jobs = JobRepository(db)
    return await jobs.create(
        owner_id=owner_id,
        device_id=device_id,
        source_url="https://x",
        status=JobStatus.QUEUED,
        current_stage="q",
        progress=0.0,
        config_snapshot={},
        **extra,
    )


# ─── repositories.py ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_update_approval_existing(db):
    """389-390: update_approval sets status on an existing clip."""
    job = await _make_job(db)
    clips = ClipRepository(db)
    clip = await clips.create(job_id=job.id, rank=0, start_secs=0, end_secs=1, title="T")
    await clips.update_approval(clip.id, "approved")
    refreshed = await clips.get(clip.id, with_overlays=False)
    assert refreshed.approval_status == "approved"


@pytest.mark.asyncio
async def test_device_claim_dev_fallback_with_other_device(db, monkeypatch):
    """677-683: dev-only claim of anonymous jobs bound to a stale device id."""
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "environment", "development")
    user = await _make_user(db, "devclaim")
    repo = DeviceRepository(db)
    # Device rows must exist first (jobs.device_id has an FK to local_devices).
    stale = await repo.get_or_create("stale-device-9999")
    await db.flush()
    # Anonymous job with a non-null device id that differs from the claim id,
    # so the tagged + legacy updates both match zero rows.
    await _make_job(db, owner_id=None, device_id=stale.id)
    count = await repo.claim_for_user("fresh-device-0001", user.id)
    assert count >= 1


@pytest.mark.asyncio
async def test_license_revoke_sets_status(db):
    """774: revoke marks the license revoked."""
    repo = InstallLicenseRepository(db)
    lic = await repo.create_issued(
        license_key_hash=uuid.uuid4().hex,
        tier=UserTier.PRO,
        order_id=f"rev-{datetime.now().timestamp()}",
        customer_email="rev@test.local",
    )
    revoked = await repo.revoke(lic)
    assert revoked.status == "revoked"


@pytest.mark.asyncio
async def test_publish_get_for_user_missing_job(db):
    """977: get_for_user returns None when the publish job does not exist."""
    repo = PublishJobRepository(db)
    assert await repo.get_for_user("nope", "user-x") is None


@pytest.mark.asyncio
async def test_publish_get_for_user_clip_missing():
    """981-984: clip-based publish job whose clip row is gone -> None.

    A dangling clip_id cannot be inserted (FK), so drive the branch with a
    mocked session where the clip lookup returns None.
    """
    from types import SimpleNamespace

    repo = PublishJobRepository(MagicMock())
    job = SimpleNamespace(id="pj1", vault_clip_id=None, clip_id="c-gone")
    repo.get = AsyncMock(return_value=job)
    repo.db.get = AsyncMock(return_value=None)
    assert await repo.get_for_user("pj1", "user-x") is None


@pytest.mark.asyncio
async def test_publish_get_for_user_no_ids(db):
    """987: publish job with neither clip_id nor vault_clip_id -> None."""
    repo = PublishJobRepository(db)
    pj = await repo.create(
        vault_clip_id=None,
        clip_id=None,
        platform="youtube_shorts",
        title="T",
        description="",
        status="pending",
    )
    assert await repo.get_for_user(pj.id, "user-x") is None


@pytest.mark.asyncio
async def test_publish_list_for_user_includes_vault(db):
    """1072-1074: list_for_user merges vault-based publish jobs."""
    user = await _make_user(db, "listpub")
    vault_repo = VaultClipRepository(db)
    vc = await vault_repo.create(
        user_id=user.id, source_job_id=None, title="VC", duration_secs=12.0,
    )
    pub_repo = PublishJobRepository(db)
    await pub_repo.create(
        vault_clip_id=vc.id,
        clip_id=None,
        platform="youtube_shorts",
        title="T",
        description="",
        status="pending",
    )
    rows = await pub_repo.list_for_user(user.id)
    assert any(r.vault_clip_id == vc.id for r in rows)


# ─── auth_service.py ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authenticate_wrong_password(db):
    """63: authenticate rejects a bad password."""
    from backend.middleware.auth import hash_password
    from core.errors import AuthError

    users = UserRepository(db)
    email = f"wrongpw-{uuid.uuid4().hex[:8]}@test.local"
    await users.create(email=email, hashed_password=hash_password("correct-pw-123"))
    svc = AuthService(db, get_settings())
    with pytest.raises(AuthError):
        await svc.authenticate(email, "totally-wrong")


def test_configure_logging_json(monkeypatch):
    """main.py 47: JSON log renderer branch."""
    import backend.main as main_mod

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "log_json", True)
    monkeypatch.setattr(main_mod, "get_settings", lambda: cfg)
    try:
        main_mod._configure_logging()
    finally:
        monkeypatch.undo()
        main_mod._configure_logging()  # restore console renderer for other tests


@pytest.mark.asyncio
async def test_register_creates_user(db):
    """52: AuthService.register persists a new user (direct call)."""
    svc = AuthService(db, get_settings())
    email = f"reg-{uuid.uuid4().hex[:8]}@test.local"
    user = await svc.register(email, "password123", display_name="Reg")
    assert user.email == email
    assert user.display_name == "Reg"


@pytest.mark.asyncio
async def test_password_reset_roundtrip(db):
    """126-130: reset_password consumes a valid reset token."""
    from backend.middleware.auth import hash_password, verify_password

    users = UserRepository(db)
    email = f"reset-{uuid.uuid4().hex[:8]}@test.local"
    await users.create(email=email, hashed_password=hash_password("original-123"))
    svc = AuthService(db, get_settings())

    result = await svc.create_password_reset(email)
    assert result is not None
    raw_token, _user = result
    await db.commit()

    user = await svc.reset_password(raw_token, "fresh-secret-456")
    refreshed = await users.get(user.id)
    assert verify_password("fresh-secret-456", refreshed.hashed_password)


# ─── models.py _ulid ImportError fallback (56-57) ─────────────────────────────

def test_ulid_import_error_falls_back_to_uuid(monkeypatch):
    import backend.db.models as models

    monkeypatch.setitem(sys.modules, "ulid", None)  # forces ImportError
    value = models._ulid()
    assert isinstance(value, str) and len(value) >= 16


# ─── session.py sqlite pragma listener (54-56) ────────────────────────────────

@pytest.mark.asyncio
async def test_sqlite_engine_enables_foreign_keys(monkeypatch):
    from sqlalchemy import text

    import backend.db.session as session_mod

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.database, "url", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(cfg.database, "sync_url", "sqlite:///:memory:")
    # Force a fresh engine build so the sqlite branch + pragma listener run.
    await session_mod.dispose_engine()
    engine = session_mod.get_engine(cfg)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA foreign_keys"))
            assert result.scalar() == 1
    finally:
        await session_mod.dispose_engine()


# ─── middleware/auth.py get_current_user_id branches (110, 124-125, 129) ──────

@pytest.mark.asyncio
async def test_get_current_user_id_missing_header_when_not_anonymous(monkeypatch):
    from fastapi import HTTPException

    from backend.middleware import auth as auth_mw

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.auth, "allow_anonymous", False)
    with pytest.raises(HTTPException):
        await auth_mw.get_current_user_id(authorization=None, device_id=None)


@pytest.mark.asyncio
async def test_get_current_user_id_invalid_and_wrong_type():
    from fastapi import HTTPException

    from backend.middleware import auth as auth_mw
    from core.config import get_settings as gs

    cfg = gs()
    # invalid token -> 401 (124-125)
    with pytest.raises(HTTPException):
        await auth_mw.get_current_user_id(authorization="Bearer not-a-jwt", device_id=None)

    # wrong token type (refresh used as access) -> 401 (129)
    refresh = auth_mw.create_refresh_token("user-1", cfg)
    with pytest.raises(HTTPException):
        await auth_mw.get_current_user_id(authorization=f"Bearer {refresh}", device_id=None)


# ─── job_service.cancel_job broker revoke failure (179-180) ───────────────────

@pytest.mark.asyncio
async def test_cancel_job_swallows_broker_revoke_error(db, monkeypatch):
    from backend.middleware.scope import RequestScope
    from backend.services.job_service import JobService
    from core.celery_app import celery_app

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    user = await _make_user(db, "cancel")
    job = await _make_job(db, owner_id=user.id, celery_task_id="task-123")
    await db.commit()

    svc = JobService(db, cfg, MagicMock())
    with patch.object(celery_app.control, "revoke", side_effect=RuntimeError("no broker")):
        await svc.cancel_job(job.id, RequestScope(user_id=user.id, device_id=None))
    refreshed = await JobRepository(db).get(job.id)
    assert refreshed.status == JobStatus.CANCELLED
