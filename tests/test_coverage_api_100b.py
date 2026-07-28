"""Line-coverage sweep, part 2: commerce webhook email branch, license
email-linkage, health probe branches, upload audio gate, SSE cursor parse.

Async handlers use mocked dependencies (see test_coverage_api_100 for why).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.commerce as commerce_api
import backend.api.health as health_api
import backend.api.jobs as jobs_api
import backend.api.license as license_api
import backend.api.uploads as uploads_api
from backend.db.models import UserTier
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id
from backend.middleware.scope import RequestScope, get_request_scope
from backend.services.job_service import ALLOWED_AUDIO_UPLOAD_TYPES
from core.config import get_settings

WEBHOOK_SECRET = "api100b-webhook-secret"


def _sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _override_db(app):
    async def fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_db


# ─── commerce.py: order_created email enqueue failure (159-160) ───────────────

@pytest.mark.asyncio
async def test_webhook_email_enqueue_failure(app, client, monkeypatch):
    cfg = get_settings()
    old_secret = cfg.commerce.lemon_squeezy_webhook_secret
    old_variants = cfg.commerce.audio_ingest_variant_ids
    cfg.commerce.lemon_squeezy_webhook_secret = WEBHOOK_SECRET
    cfg.commerce.audio_ingest_variant_ids = "vaudio"  # exercises audio order tagging (119)

    repo = MagicMock()
    repo.get_by_order_id = AsyncMock(return_value=None)
    repo.create_issued = AsyncMock(return_value=SimpleNamespace(id="lic1"))
    monkeypatch.setattr(commerce_api, "InstallLicenseRepository", lambda db: repo)
    _override_db(app)
    try:
        body = json.dumps({
            "meta": {"event_name": "order_created"},
            "data": {"id": uuid.uuid4().hex[:12], "attributes": {
                "user_email": "b@x.com",
                "first_order_item": {"variant_id": "vaudio"},
            }},
        }).encode()
        with patch.object(
            commerce_api, "dispatch_task_by_name", side_effect=RuntimeError("broker down"),
        ):
            resp = await client.post(
                "/api/commerce/webhooks/lemon-squeezy",
                content=body,
                headers={"X-Signature": _sign(body)},
            )
        assert resp.status_code == 200
        assert resp.json()["license_key"].startswith("SCPRO-")
    finally:
        cfg.commerce.lemon_squeezy_webhook_secret = old_secret
        cfg.commerce.audio_ingest_variant_ids = old_variants
        app.dependency_overrides.pop(get_db, None)


# ─── license.py: activation links license to user by purchase email (95-105) ──

@pytest.mark.asyncio
async def test_activate_links_license_by_purchase_email(app, client, monkeypatch):
    lic = SimpleNamespace(
        id="lic1",
        status="issued",
        machine_id=None,
        activation_count=0,
        tier=UserTier.PRO,
        user_id=None,
        customer_email="Buyer@Example.com",
        order_id=None,
        capabilities=None,
    )
    repo = MagicMock()
    repo.get_by_key_hash = AsyncMock(return_value=lic)
    repo.mark_activated = AsyncMock()
    monkeypatch.setattr(license_api, "InstallLicenseRepository", lambda db: repo)

    entitlement = SimpleNamespace(
        expires_at=datetime.now(timezone.utc),
        tier=SimpleNamespace(value="pro"),
        capabilities=["studio", "publisher"],
    )
    monkeypatch.setattr(
        license_api, "activate_license_key", lambda *a, **k: ("jwt-token", entitlement),
    )

    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=SimpleNamespace(id="user-9"))
    monkeypatch.setattr(license_api, "UserRepository", lambda db: user_repo)
    link = AsyncMock()
    monkeypatch.setattr(license_api, "link_license_to_user", link)

    _override_db(app)
    app.dependency_overrides[get_current_user_id] = lambda: None
    try:
        resp = await client.post(
            "/api/license/activate",
            json={"license_key": "SCPRO-AAAA-BBBB-CCCC-DDDD", "machine_id": "machine-abcdef12"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["tier"] == "pro"
        link.assert_awaited()
        user_repo.get_by_email.assert_awaited_with("buyer@example.com")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_activate_links_authed_user_swallows_link_error(app, client, monkeypatch):
    """97 (link by authed user) + 104-105 (best-effort linkage never fails activation)."""
    lic = SimpleNamespace(
        id="lic2", status="issued", machine_id="machine-abcdef12", activation_count=0,
        tier=UserTier.PRO, user_id=None, customer_email=None,
        order_id=None, capabilities=None,
    )
    repo = MagicMock()
    repo.get_by_key_hash = AsyncMock(return_value=lic)
    repo.mark_activated = AsyncMock()
    monkeypatch.setattr(license_api, "InstallLicenseRepository", lambda db: repo)
    entitlement = SimpleNamespace(
        expires_at=None,
        tier=SimpleNamespace(value="pro"),
        capabilities=["studio", "publisher"],
    )
    monkeypatch.setattr(license_api, "activate_license_key", lambda *a, **k: ("jwt", entitlement))
    monkeypatch.setattr(
        license_api, "link_license_to_user", AsyncMock(side_effect=RuntimeError("link boom")),
    )
    _override_db(app)
    app.dependency_overrides[get_current_user_id] = lambda: "authed-user"
    try:
        resp = await client.post(
            "/api/license/activate",
            json={"license_key": "SCPRO-AAAA-BBBB-CCCC-DDDD", "machine_id": "machine-abcdef12"},
        )
        assert resp.status_code == 200, resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_license_status_no_persisted_token(app, client, monkeypatch):
    """133: no persisted entitlement -> inactive with the install's base tier."""
    monkeypatch.setattr(license_api, "load_persisted_entitlement", lambda cfg: "")
    resp = await client.get("/api/license/status", params={"machine_id": "machine-abc123"})
    assert resp.status_code == 200
    assert resp.json()["active"] is False


# ─── uploads.py: audio upload rejected without the add-on (54) ────────────────

@pytest.mark.asyncio
async def test_upload_init_audio_disabled(client, monkeypatch):
    audio_type = sorted(ALLOWED_AUDIO_UPLOAD_TYPES)[0]

    async def _deny(*_a, **_k):
        return False

    monkeypatch.setattr(uploads_api, "scope_allows_audio_ingest", _deny)
    resp = await client.post(
        "/api/uploads/init",
        json={"filename": "clip.mp3", "content_type": audio_type},
    )
    assert resp.status_code == 403


# ─── health.py: db ok (42) + inprocess redis (50) ────────────────────────────

@pytest.mark.asyncio
async def test_health_inprocess_ok(app, client, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    _override_db(app)
    storage = MagicMock()
    storage.list_prefix.return_value = []
    monkeypatch.setattr(health_api, "make_storage", lambda cfg: storage)
    try:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["database"] is True
        assert body["redis"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_health_redis_failure(app, client, monkeypatch):
    """57-58: redis ping failure marks redis unhealthy without erroring the probe."""
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    _override_db(app)
    storage = MagicMock()
    storage.list_prefix.return_value = []
    monkeypatch.setattr(health_api, "make_storage", lambda cfg: storage)

    bad_redis = MagicMock()
    bad_redis.ping = AsyncMock(side_effect=RuntimeError("no redis"))
    bad_redis.close = AsyncMock()
    monkeypatch.setattr(health_api.aioredis, "from_url", lambda *a, **k: bad_redis)
    try:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["redis"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)


# ─── jobs.py: SSE progress cursor parse (511-524) ────────────────────────────

@pytest.mark.asyncio
async def test_progress_stream_parses_last_event_id(app, client, monkeypatch):
    async def _fake_stream(job_id, cfg, *, last_event_id=None):
        yield f"data: cursor={last_event_id}\n\n"

    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr(jobs_api, "_get_service", lambda db: svc)
    monkeypatch.setattr(jobs_api, "stream_job_progress", _fake_stream)

    _override_db(app)
    app.dependency_overrides[get_request_scope] = lambda: RequestScope(
        user_id=None, device_id="test-device-0001",
    )
    try:
        ok = await client.get(
            "/api/jobs/job-xyz/progress",
            headers={"Last-Event-Id": "7"},
        )
        assert ok.status_code == 200
        assert "cursor=7" in ok.text

        # Non-numeric id -> ValueError branch resets the cursor (515-516).
        bad = await client.get(
            "/api/jobs/job-xyz/progress",
            headers={"Last-Event-Id": "not-a-number"},
        )
        assert bad.status_code == 200
        assert "cursor=None" in bad.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_request_scope, None)
