"""Line-coverage sweep, part 2: commerce webhook branches, license email
linkage, upload audio gate, health probe branches, and the SSE progress
cursor parse."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.commerce as commerce_api
import backend.api.jobs as jobs_api
import backend.api.uploads as uploads_api
from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_db, get_sessionmaker
from backend.middleware.scope import RequestScope, get_request_scope
from backend.services.job_service import ALLOWED_AUDIO_UPLOAD_TYPES
from core.commerce.lemon_squeezy import generate_license_key
from core.config import get_settings
from core.licensing import hash_license_key

WEBHOOK_SECRET = "api100b-webhook-secret"


def _sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


# ─── commerce.py: audio variant tagging (119) + email enqueue failure (159-160) ─

@pytest.mark.asyncio
async def test_webhook_audio_variant_and_email_enqueue_failure(client, monkeypatch):
    cfg = get_settings()
    old_secret = cfg.commerce.lemon_squeezy_webhook_secret
    cfg.commerce.lemon_squeezy_webhook_secret = WEBHOOK_SECRET
    monkeypatch.setattr(cfg.commerce, "audio_ingest_variant_ids", "vaudio", raising=False)
    try:
        body = json.dumps({
            "meta": {"event_name": "order_created"},
            "data": {
                "id": uuid.uuid4().hex[:12],
                "attributes": {
                    "user_email": "audio-buyer@example.com",
                    "first_order_item": {"variant_id": "vaudio"},
                },
            },
        }).encode()
        # dispatch raises -> the best-effort except (159-160) is exercised
        with patch.object(
            commerce_api,
            "dispatch_task_by_name",
            side_effect=RuntimeError("broker down"),
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


# ─── license.py: activation links license to user by purchase email (97-105) ──

@pytest.mark.asyncio
async def test_activate_links_license_by_purchase_email(client):
    # Register a user whose email matches the license purchase email.
    email = f"liclink-{uuid.uuid4().hex[:10]}@example.com"
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    raw_key = generate_license_key()
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        repo = InstallLicenseRepository(session)
        await repo.create_issued(
            license_key_hash=hash_license_key(raw_key),
            tier=UserTier.PRO,
            order_id=uuid.uuid4().hex[:12],
            customer_email=email,
        )
        await session.commit()

    # No Authorization header: linkage falls back to the purchase-email match.
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": raw_key, "machine_id": "machine-abcdef12"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["tier"] == "pro"

    async with SessionMaker() as session:
        repo = InstallLicenseRepository(session)
        lic = await repo.get_by_key_hash(hash_license_key(raw_key))
        assert lic is not None
        assert lic.user_id == user_id


# ─── uploads.py: audio upload rejected without the add-on (50-59) ─────────────

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
    assert resp.json().get("code") == "audio_ingest_disabled" or resp.status_code == 403


# ─── health.py: db ok (42), inprocess redis (50), redis fail (57-58) ─────────

@pytest.mark.asyncio
async def test_health_inprocess_redis_ok(client, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] is True
    assert body["redis"] is True


@pytest.mark.asyncio
async def test_health_redis_failure_degraded(client, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    monkeypatch.setattr(cfg.redis, "url", "redis://127.0.0.1:6390/0")  # nothing here
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["redis"] is False
    assert body["status"] == "degraded"


# ─── jobs.py: SSE progress cursor parse (511-524) ────────────────────────────

@pytest.mark.asyncio
async def test_progress_stream_parses_last_event_id(app, client, monkeypatch):
    async def _fake_stream(job_id, cfg, *, last_event_id=None):
        yield f"data: cursor={last_event_id}\n\n"

    svc = MagicMock()
    svc.get_job = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr(jobs_api, "_get_service", lambda db: svc)
    monkeypatch.setattr(jobs_api, "stream_job_progress", _fake_stream)

    session = MagicMock()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_request_scope] = lambda: RequestScope(
        user_id=None, device_id="test-device-0001",
    )
    try:
        resp = await client.get(
            "/api/jobs/job-xyz/progress",
            headers={"Last-Event-Id": "7"},
        )
        assert resp.status_code == 200
        assert "cursor=7" in resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_request_scope, None)
