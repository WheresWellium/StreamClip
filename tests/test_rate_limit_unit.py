from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException
from backend.middleware import rate_limit as rl

@pytest.mark.asyncio
async def test_get_redis_singleton():
    cfg = MagicMock()
    cfg.redis.url = "redis://localhost:6379/0"
    with patch("backend.middleware.rate_limit.aioredis.from_url") as fr:
        fr.return_value = MagicMock()
        r1 = await rl._get_redis(cfg)
        r2 = await rl._get_redis(cfg)
        assert r1 is r2

@pytest.mark.asyncio
async def test_check_window_allowed():
    redis = MagicMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[None, 0, None, None])
    redis.pipeline.return_value = pipe
    ok, rem = await rl._check_window(redis, "k", window_secs=60, limit=10)
    assert ok is True

@pytest.mark.asyncio
async def test_rate_limit_request_blocks():
    req = MagicMock()
    req.client.host = "1.2.3.4"
    req.state = MagicMock()
    cfg = MagicMock()
    cfg.rate_limit.enabled = True
    cfg.rate_limit.requests_per_minute = 1
    with patch("backend.middleware.rate_limit.get_settings", return_value=cfg):
        with patch("backend.middleware.rate_limit._get_redis", new_callable=AsyncMock) as gr:
            gr.return_value = AsyncMock()
            with patch("backend.middleware.rate_limit._check_window", new_callable=AsyncMock, return_value=(False, 0)):
                with pytest.raises(HTTPException) as exc:
                    await rl.rate_limit_request(req, user_id=None)
                assert exc.value.status_code == 429

@pytest.mark.asyncio
async def test_rate_limit_job_creation_blocks():
    req = MagicMock()
    req.client.host = "1.2.3.4"
    cfg = MagicMock()
    cfg.rate_limit.enabled = True
    cfg.rate_limit.jobs_per_hour = 1
    with patch("backend.middleware.rate_limit.get_settings", return_value=cfg):
        with patch("backend.middleware.rate_limit._get_redis", new_callable=AsyncMock):
            with patch("backend.middleware.rate_limit._check_window", new_callable=AsyncMock, return_value=(False, 0)):
                with pytest.raises(HTTPException):
                    await rl.rate_limit_job_creation(req, user_id="u1")
