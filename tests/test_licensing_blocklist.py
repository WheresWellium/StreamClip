"""Entitlement JWT blocklist on revoke."""

from __future__ import annotations

import pytest

from backend.db.models import UserTier
from core.licensing import (
    create_entitlement_token,
    is_entitlement_hash_revoked,
    revoke_entitlement_hash,
    verify_entitlement_token,
)


def test_revoked_hash_rejects_entitlement_token(monkeypatch: pytest.MonkeyPatch) -> None:
    store: set[str] = set()

    class FakeRedis:
        def sadd(self, key: str, *members: str) -> int:
            store.update(members)
            return len(members)

        def sismember(self, key: str, member: str) -> bool:
            return member in store

    monkeypatch.setattr("core.celery_app.get_redis", lambda: FakeRedis())

    key_hash = "ab" * 32
    token = create_entitlement_token(
        tier=UserTier.PRO,
        machine_id="m1",
        license_key_hash=key_hash,
        expires_at=None,
    )
    assert verify_entitlement_token(token, machine_id="m1").tier == UserTier.PRO
    revoke_entitlement_hash(key_hash)
    assert is_entitlement_hash_revoked(key_hash)
    with pytest.raises(ValueError, match="revoked"):
        verify_entitlement_token(token, machine_id="m1")
