"""Rate limit helper tests."""

from __future__ import annotations

import pytest

from backend.middleware.rate_limit import _check_window


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, float]] = {}

    def pipeline(self):
        return self

    def zremrangebyscore(self, key, _min, _max):
        self._key = key
        return self

    def zcard(self, key):
        self._key = key
        return self

    def zadd(self, key, mapping):
        self.store.setdefault(key, {}).update(mapping)
        return self

    def expire(self, key, _ttl):
        return self

    async def execute(self):
        key = getattr(self, "_key", "default")
        count = len(self.store.get(key, {}))
        return (0, count, 0, True)


@pytest.mark.asyncio
async def test_rate_limit_window_allows_under_limit():
    redis = FakeRedis()
    allowed, remaining = await _check_window(redis, "test", window_secs=60, limit=5)
    assert allowed is True
    assert remaining >= 0
