"""License chain: commerce webhook issuance → key activation → entitlement.

DB access is faked at the repository seam so these run without Postgres.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

import pytest

import backend.api.commerce as commerce_api
import backend.api.license as license_api
from backend.db.models import UserTier
from backend.db.session import get_db
from core.commerce.lemon_squeezy import (
    generate_license_key,
    parse_order_event,
    verify_webhook_signature,
)
from core.config import get_settings
from core.licensing import (
    activate_license_key,
    hash_license_key,
    verify_entitlement_token,
)

WEBHOOK_SECRET = "test-webhook-secret"


def _sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


class FakeLicenseRow:
    def __init__(self, **kw):
        self.id = kw.get("id", "lic1")
        self.license_key_hash = kw["license_key_hash"]
        self.tier = kw.get("tier", UserTier.PRO)
        self.machine_id = kw.get("machine_id")
        self.entitlement_jwt = kw.get("entitlement_jwt")
        self.expires_at = kw.get("expires_at")
        self.activated_at = kw.get("activated_at")
        self.status = kw.get("status", "issued")
        self.order_id = kw.get("order_id")
        self.customer_email = kw.get("customer_email")
        self.activation_count = kw.get("activation_count", 0)


class FakeLicenseRepo:
    """In-memory stand-in with the same surface as InstallLicenseRepository."""

    rows: list[FakeLicenseRow] = []

    def __init__(self, db) -> None:
        self.db = db

    @classmethod
    def reset(cls) -> None:
        cls.rows = []

    async def get_by_key_hash(self, license_key_hash):
        return next(
            (r for r in self.rows if r.license_key_hash == license_key_hash), None,
        )

    async def get_by_order_id(self, order_id):
        return next((r for r in self.rows if r.order_id == order_id), None)

    async def create_issued(self, *, license_key_hash, tier, order_id=None, customer_email=None):
        row = FakeLicenseRow(
            license_key_hash=license_key_hash,
            tier=tier,
            order_id=order_id,
            customer_email=customer_email,
        )
        self.rows.append(row)
        return row

    async def mark_activated(
        self, lic, *, machine_id, entitlement_jwt, expires_at, count_activation,
    ):
        lic.machine_id = machine_id
        lic.entitlement_jwt = entitlement_jwt
        lic.expires_at = expires_at
        lic.activated_at = datetime.now()
        lic.status = "activated"
        if count_activation:
            lic.activation_count += 1
        return lic


class FakeSession:
    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


@pytest.fixture
def license_env(app, monkeypatch, tmp_path):
    """Wire fakes: repo, DB session, webhook secret, license file path."""
    cfg = get_settings()
    old_secret = cfg.commerce.lemon_squeezy_webhook_secret
    old_license_file = cfg.licensing.license_file
    cfg.commerce.lemon_squeezy_webhook_secret = WEBHOOK_SECRET
    cfg.licensing.license_file = tmp_path / "license.json"

    FakeLicenseRepo.reset()
    monkeypatch.setattr(commerce_api, "InstallLicenseRepository", FakeLicenseRepo)
    monkeypatch.setattr(license_api, "InstallLicenseRepository", FakeLicenseRepo)

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    yield
    app.dependency_overrides.pop(get_db, None)
    cfg.commerce.lemon_squeezy_webhook_secret = old_secret
    cfg.licensing.license_file = old_license_file


# ─── Pure helpers ────────────────────────────────────────────────────────────

def test_generate_license_key_format():
    key = generate_license_key()
    assert key.startswith("SCPRO-")
    assert len(key) == len("SCPRO-XXXX-XXXX-XXXX-XXXX")


def test_verify_webhook_signature_roundtrip():
    body = b'{"a": 1}'
    assert verify_webhook_signature(body, _sign(body), WEBHOOK_SECRET)
    assert not verify_webhook_signature(body, "bad", WEBHOOK_SECRET)
    assert not verify_webhook_signature(body, _sign(body), "")


def test_parse_license_key_created_event():
    event = parse_order_event({
        "meta": {"event_name": "license_key_created"},
        "data": {"id": "9", "attributes": {"key": "LSKEY-1234-5678-9012", "order_id": 42}},
    })
    assert event["license_key"] == "LSKEY-1234-5678-9012"
    assert event["order_id"] == "42"
    assert event["license_key_hash"] == hash_license_key("LSKEY-1234-5678-9012")


def test_parse_order_created_has_no_key():
    event = parse_order_event({
        "meta": {"event_name": "order_created"},
        "data": {"id": "77", "attributes": {"user_email": "a@b.co"}},
    })
    assert event["license_key"] == ""
    assert event["order_id"] == "77"
    assert event["customer_email"] == "a@b.co"


def test_entitlement_jwt_roundtrip(tmp_path):
    cfg = get_settings()
    old = cfg.licensing.license_file
    cfg.licensing.license_file = tmp_path / "license.json"
    try:
        key = generate_license_key()
        token, ent = activate_license_key(key, "machine-abc-123", tier=UserTier.PRO, cfg=cfg)
        assert ent.tier is UserTier.PRO
        verified = verify_entitlement_token(token, machine_id="machine-abc-123", cfg=cfg)
        assert verified.license_key_hash == hash_license_key(key)
        with pytest.raises(ValueError):
            verify_entitlement_token(token, machine_id="other-machine", cfg=cfg)
    finally:
        cfg.licensing.license_file = old


# ─── Webhook endpoint ────────────────────────────────────────────────────────

async def test_webhook_fails_closed_without_secret(client, license_env):
    get_settings().commerce.lemon_squeezy_webhook_secret = ""
    resp = await client.post("/api/commerce/webhooks/lemon-squeezy", content=b"{}")
    assert resp.status_code == 503


async def test_webhook_rejects_bad_signature(client, license_env):
    resp = await client.post(
        "/api/commerce/webhooks/lemon-squeezy",
        content=b"{}",
        headers={"X-Signature": "forged"},
    )
    assert resp.status_code == 401


async def test_webhook_rejects_invalid_json(client, license_env):
    body = b"not-json"
    resp = await client.post(
        "/api/commerce/webhooks/lemon-squeezy",
        content=body,
        headers={"X-Signature": _sign(body)},
    )
    assert resp.status_code == 400


async def test_order_created_issues_and_persists_key(client, license_env):
    body = json.dumps({
        "meta": {"event_name": "order_created"},
        "data": {"id": "555", "attributes": {"user_email": "buyer@example.com"}},
    }).encode()
    resp = await client.post(
        "/api/commerce/webhooks/lemon-squeezy",
        content=body,
        headers={"X-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    key = resp.json()["license_key"]
    assert key.startswith("SCPRO-")

    rows = FakeLicenseRepo.rows
    assert len(rows) == 1
    assert rows[0].license_key_hash == hash_license_key(key)
    assert rows[0].order_id == "555"
    assert rows[0].customer_email == "buyer@example.com"
    assert rows[0].status == "issued"

    # Redelivery of the same order must not mint a second key.
    resp2 = await client.post(
        "/api/commerce/webhooks/lemon-squeezy",
        content=body,
        headers={"X-Signature": _sign(body)},
    )
    assert resp2.status_code == 200
    assert resp2.json()["license_key"] is None
    assert len(FakeLicenseRepo.rows) == 1


async def test_license_key_created_records_ls_key(client, license_env):
    body = json.dumps({
        "meta": {"event_name": "license_key_created"},
        "data": {"id": "3", "attributes": {"key": "LS-ABCD-EFGH-IJKL-MNOP", "order_id": 91}},
    }).encode()
    resp = await client.post(
        "/api/commerce/webhooks/lemon-squeezy",
        content=body,
        headers={"X-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    assert FakeLicenseRepo.rows[0].license_key_hash == hash_license_key("LS-ABCD-EFGH-IJKL-MNOP")


async def test_webhook_ignores_unknown_event(client, license_env):
    body = json.dumps({"meta": {"event_name": "subscription_updated"}}).encode()
    resp = await client.post(
        "/api/commerce/webhooks/lemon-squeezy",
        content=body,
        headers={"X-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


# ─── Activation endpoint ─────────────────────────────────────────────────────

async def _issue_key() -> str:
    key = generate_license_key()
    repo = FakeLicenseRepo(None)
    await repo.create_issued(
        license_key_hash=hash_license_key(key), tier=UserTier.PRO, order_id="o1",
    )
    return key


async def test_activate_unknown_key_rejected(client, license_env):
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": "SCPRO-0000-0000-0000-0000", "machine_id": "machine-1"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_license_key"


async def test_activate_issued_key_grants_pro(client, license_env):
    key = await _issue_key()
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": key, "machine_id": "machine-abc-1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "pro"

    row = FakeLicenseRepo.rows[0]
    assert row.status == "activated"
    assert row.machine_id == "machine-abc-1"
    assert row.activation_count == 1

    ent = verify_entitlement_token(data["entitlement_jwt"], machine_id="machine-abc-1")
    assert ent.tier is UserTier.PRO


async def test_activate_revoked_key_rejected(client, license_env):
    key = await _issue_key()
    FakeLicenseRepo.rows[0].status = "revoked"
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": key, "machine_id": "machine-1"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "license_revoked"


async def test_activation_limit_enforced_across_machines(client, license_env):
    key = await _issue_key()
    max_activations = get_settings().licensing.max_activations
    for i in range(max_activations):
        resp = await client.post(
            "/api/license/activate",
            json={"license_key": key, "machine_id": f"machine-{i:04d}"},
        )
        assert resp.status_code == 200
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": key, "machine_id": "machine-one-too-many"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "activation_limit_reached"

    # Re-activating on the last bound machine is still allowed.
    resp = await client.post(
        "/api/license/activate",
        json={"license_key": key, "machine_id": f"machine-{max_activations - 1:04d}"},
    )
    assert resp.status_code == 200
