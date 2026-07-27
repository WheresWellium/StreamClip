"""Revoking a key must stop the install, not linger for the life of the JWT."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.db.models import InstallLicense, UserTier
from backend.db.session import get_sessionmaker
from core.config import get_settings
from core.licensing import (
    activate_license_key,
    clear_persisted_entitlement,
    create_entitlement_token,
    hash_license_key,
    load_persisted_entitlement,
    persist_entitlement_token,
    renewal_window_days,
    verify_entitlement_token,
)


@pytest.fixture
def license_file(tmp_path):
    cfg = get_settings()
    original = cfg.licensing.license_file
    cfg.licensing.license_file = tmp_path / "license.json"
    yield cfg
    cfg.licensing.license_file = original


async def _seed_license(**overrides) -> InstallLicense:
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        lic = InstallLicense(
            license_key_hash=overrides.pop("license_key_hash", uuid.uuid4().hex[:64]),
            tier=overrides.pop("tier", UserTier.PRO),
            status=overrides.pop("status", "activated"),
            **overrides,
        )
        session.add(lic)
        await session.commit()
        return lic


# ─── Local token teardown ────────────────────────────────────────────────────

def test_clear_persisted_entitlement_removes_the_token(license_file):
    cfg = license_file
    activate_license_key(
        "SCPRO-AAAA-BBBB-CCCC-DDDD", "machine-clear", tier=UserTier.PRO, cfg=cfg,
    )
    assert load_persisted_entitlement(cfg) is not None

    clear_persisted_entitlement(cfg)
    assert load_persisted_entitlement(cfg) is None


def test_clear_persisted_entitlement_is_safe_when_absent(license_file):
    clear_persisted_entitlement(license_file)
    clear_persisted_entitlement(license_file)  # idempotent
    assert load_persisted_entitlement(license_file) is None


# ─── Status endpoint honours revocation ──────────────────────────────────────

@pytest.mark.asyncio
async def test_status_reports_revoked_and_drops_the_token(client, license_file):
    cfg = license_file
    machine_id = f"machine-{uuid.uuid4().hex[:8]}"
    key = f"SCPRO-{uuid.uuid4().hex[:16].upper()}"

    await _seed_license(
        license_key_hash=hash_license_key(key),
        machine_id=machine_id,
        status="revoked",
    )
    activate_license_key(key, machine_id, tier=UserTier.PRO, cfg=cfg)
    assert load_persisted_entitlement(cfg) is not None

    resp = await client.get("/api/license/status", params={"machine_id": machine_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is False
    assert body["revoked"] is True
    assert body["tier"] == "free"
    # The install stops presenting a token it can no longer justify.
    assert load_persisted_entitlement(cfg) is None


@pytest.mark.asyncio
async def test_status_reports_active_perpetual_license(client, license_file):
    cfg = license_file
    machine_id = f"machine-{uuid.uuid4().hex[:8]}"
    key = f"SCPRO-{uuid.uuid4().hex[:16].upper()}"

    await _seed_license(
        license_key_hash=hash_license_key(key),
        machine_id=machine_id,
        status="activated",
    )
    activate_license_key(key, machine_id, tier=UserTier.PRO, cfg=cfg)

    resp = await client.get("/api/license/status", params={"machine_id": machine_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["tier"] == "pro"
    assert body["perpetual"] is True


# ─── Expired tokens renew only while the licence is still activated ──────────

@pytest.mark.asyncio
async def test_expired_token_renews_for_an_activated_license(client, license_file):
    cfg = license_file
    machine_id = f"machine-{uuid.uuid4().hex[:8]}"
    key = f"SCPRO-{uuid.uuid4().hex[:16].upper()}"
    await _seed_license(
        license_key_hash=hash_license_key(key),
        machine_id=machine_id,
        status="activated",
    )
    _write_expired_token(cfg, machine_id, hash_license_key(key))

    resp = await client.get("/api/license/status", params={"machine_id": machine_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["tier"] == "pro"

    renewed = verify_entitlement_token(
        load_persisted_entitlement(cfg), machine_id=machine_id, cfg=cfg,
    )
    assert renewed.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_expired_token_is_discarded_without_an_activated_license(
    client, license_file,
):
    cfg = license_file
    machine_id = f"machine-{uuid.uuid4().hex[:8]}"
    _write_expired_token(cfg, machine_id, hash_license_key("SCPRO-NO-RECORD-0000"))

    resp = await client.get("/api/license/status", params={"machine_id": machine_id})
    assert resp.status_code == 200
    assert resp.json()["active"] is False
    assert load_persisted_entitlement(cfg) is None


def _write_expired_token(cfg, machine_id: str, key_hash: str) -> None:
    """Persist a token whose renewal deadline has already passed."""
    import jwt

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "type": "entitlement",
            "tier": UserTier.PRO.value,
            "machine_id": machine_id,
            "license_key_hash": key_hash,
            "license_exp": int((now + timedelta(days=36500)).timestamp()),
            "jti": uuid.uuid4().hex,
            "iat": now - timedelta(days=90),
            "exp": now - timedelta(days=1),
        },
        cfg.auth.secret_key,
        algorithm=cfg.auth.algorithm,
    )
    persist_entitlement_token(token, cfg)


# ─── Renewal window is bounded ───────────────────────────────────────────────

def test_renewal_window_tracks_offline_grace(license_file):
    cfg = license_file
    original = cfg.licensing.offline_grace_days
    try:
        cfg.licensing.offline_grace_days = 14
        assert renewal_window_days(cfg) == 14
    finally:
        cfg.licensing.offline_grace_days = original


def test_token_never_outlives_the_renewal_window(license_file):
    cfg = license_file
    token = create_entitlement_token(
        tier=UserTier.PRO,
        machine_id="machine-window",
        license_key_hash="a" * 64,
        expires_at=None,  # perpetual purchase
        cfg=cfg,
    )
    ent = verify_entitlement_token(token, machine_id="machine-window", cfg=cfg)
    limit = datetime.now(timezone.utc) + timedelta(days=renewal_window_days(cfg) + 1)
    assert ent.expires_at < limit
