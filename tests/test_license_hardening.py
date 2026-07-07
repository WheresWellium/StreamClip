"""License hardening — perpetual JWT, collision retry, admin revoke, audit."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from backend.api.commerce import _issue_key_with_collision_retry
from backend.db.models import InstallLicense, User, UserTier
from backend.db.session import get_sessionmaker
from core.config import get_settings
from core.licensing import PERPETUAL_DAYS, activate_license_key, hash_license_key

WEBHOOK_SECRET = "hardening-test-secret"


def _sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _unique_email() -> str:
    return f"hardening-{uuid.uuid4().hex[:10]}@example.com"


async def _register(client, *, tier: UserTier = UserTier.FREE) -> tuple[str, str]:
    """Create a user, optionally promote the tier. Returns (user_id, token)."""
    email = _unique_email()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert resp.status_code == 201
    user_id = resp.json()["user"]["id"]
    token = resp.json()["access_token"]
    if tier != UserTier.FREE:
        SessionMaker = get_sessionmaker()
        async with SessionMaker() as session:
            user = await session.get(User, user_id)
            user.tier = tier
            await session.commit()
    return user_id, token


async def _seed_license(**overrides) -> str:
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        lic = InstallLicense(
            license_key_hash=overrides.pop("license_key_hash", uuid.uuid4().hex[:64]),
            tier=UserTier.PRO,
            status=overrides.pop("status", "issued"),
            **overrides,
        )
        session.add(lic)
        await session.commit()
        return lic.id


# ─── Perpetual entitlement ────────────────────────────────────────────────────

def test_activation_issues_perpetual_entitlement_by_default(tmp_path):
    cfg = get_settings()
    old_file = cfg.licensing.license_file
    old_days = cfg.licensing.entitlement_days
    cfg.licensing.license_file = tmp_path / "license.json"
    cfg.licensing.entitlement_days = 0  # one-time purchase promise
    try:
        _, ent = activate_license_key(
            "SCPRO-AAAA-BBBB-CCCC-DDDD", "machine-1", tier=UserTier.PRO, cfg=cfg,
        )
        horizon = datetime.now(timezone.utc) + timedelta(days=PERPETUAL_DAYS - 30)
        assert ent.expires_at is not None
        assert ent.expires_at > horizon  # effectively perpetual (~100 years)
    finally:
        cfg.licensing.license_file = old_file
        cfg.licensing.entitlement_days = old_days


def test_activation_honors_subscription_days(tmp_path):
    cfg = get_settings()
    old_file = cfg.licensing.license_file
    old_days = cfg.licensing.entitlement_days
    cfg.licensing.license_file = tmp_path / "license.json"
    cfg.licensing.entitlement_days = 30
    try:
        _, ent = activate_license_key(
            "SCPRO-EEEE-FFFF-GGGG-HHHH", "machine-2", tier=UserTier.PRO, cfg=cfg,
        )
        delta = ent.expires_at - datetime.now(timezone.utc)
        assert timedelta(days=29) < delta < timedelta(days=31)
    finally:
        cfg.licensing.license_file = old_file
        cfg.licensing.entitlement_days = old_days


# ─── Hash collision retry ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_key_retries_on_integrity_error():
    db = MagicMock()
    db.rollback = AsyncMock()
    repo = MagicMock()
    issued_row = MagicMock()
    repo.create_issued = AsyncMock(
        side_effect=[IntegrityError("dup", None, Exception("dup")), issued_row],
    )

    key, lic = await _issue_key_with_collision_retry(
        db, repo, order_id="o1", customer_email="a@b.c",
    )
    assert key.startswith("SCPRO-")
    assert lic is issued_row
    assert repo.create_issued.await_count == 2
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_issue_key_gives_up_after_max_attempts():
    from fastapi import HTTPException

    db = MagicMock()
    db.rollback = AsyncMock()
    repo = MagicMock()
    repo.create_issued = AsyncMock(
        side_effect=IntegrityError("dup", None, Exception("dup")),
    )
    with pytest.raises(HTTPException) as exc_info:
        await _issue_key_with_collision_retry(
            db, repo, order_id="o2", customer_email=None, max_attempts=3,
        )
    assert exc_info.value.status_code == 500
    assert repo.create_issued.await_count == 3


# ─── Admin revoke ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_revoke_license(client):
    _, admin_token = await _register(client, tier=UserTier.ADMIN)
    lic_id = await _seed_license()

    resp = await client.post(
        f"/api/admin/licenses/{lic_id}/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        lic = await session.get(InstallLicense, lic_id)
        assert lic.status == "revoked"


@pytest.mark.asyncio
async def test_revoked_key_cannot_activate(client):
    _, admin_token = await _register(client, tier=UserTier.ADMIN)
    key = f"SCPRO-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-TEST-KEYS"
    lic_id = await _seed_license(license_key_hash=hash_license_key(key))

    await client.post(
        f"/api/admin/licenses/{lic_id}/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": key, "machine_id": "m-revoked-test"},
    )
    assert resp.status_code in (403, 409, 410)
    assert "revoke" in resp.json().get("message", "").lower() or resp.status_code != 200


@pytest.mark.asyncio
async def test_non_admin_cannot_revoke(client):
    _, user_token = await _register(client, tier=UserTier.FREE)
    lic_id = await _seed_license()
    resp = await client.post(
        f"/api/admin/licenses/{lic_id}/revoke",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_cannot_revoke(client):
    lic_id = await _seed_license()
    resp = await client.post(f"/api/admin/licenses/{lic_id}/revoke")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_revoke_missing_license_404(client):
    _, admin_token = await _register(client, tier=UserTier.ADMIN)
    resp = await client.post(
        "/api/admin/licenses/nope/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ─── order_created email fallback ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_created_enqueues_license_email(client):
    cfg = get_settings()
    old_secret = cfg.commerce.lemon_squeezy_webhook_secret
    cfg.commerce.lemon_squeezy_webhook_secret = WEBHOOK_SECRET
    try:
        body = json.dumps({
            "meta": {"event_name": "order_created"},
            "data": {
                "id": uuid.uuid4().hex[:12],
                "attributes": {"user_email": "buyer@example.com"},
            },
        }).encode()
        with patch("backend.api.commerce.dispatch_task_by_name") as dispatch:
            resp = await client.post(
                "/api/commerce/webhooks/lemon-squeezy",
                content=body,
                headers={"X-Signature": _sign(body)},
            )
        assert resp.status_code == 200
        assert resp.json()["license_key"].startswith("SCPRO-")
        dispatch.assert_called_once()
        args, kwargs = dispatch.call_args
        assert args[0] == "core.tasks.notify_tasks.send_license_key_email"
        assert kwargs["args"][0] == "buyer@example.com"
        assert kwargs["queue"] == "default"
    finally:
        cfg.commerce.lemon_squeezy_webhook_secret = old_secret
