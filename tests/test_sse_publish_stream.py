"""SSE relay coverage for publish job progress streams."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import sse as sse_mod
from backend.services.sse import get_redis, stream_publish_progress
from core.config import get_settings


@pytest.mark.asyncio
async def test_stream_publish_progress_snapshot_terminal():
    cfg = get_settings()
    snapshot = json.dumps({"status": "done", "event_id": 2, "stage": "upload"})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=snapshot)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-1", cfg, heartbeat_secs=0.01)
        chunks = []
        async for chunk in gen:
            chunks.append(chunk)
            if len(chunks) > 4:
                break

    assert any("done" in c or "progress" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_progress_live_and_heartbeat():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    payloads = [
        {"type": "message", "data": json.dumps({"status": "processing", "event_id": 3})},
        None,
    ]

    async def get_message(**_kwargs):
        if payloads:
            return payloads.pop(0)
        await asyncio.sleep(0)
        return None

    mock_pubsub.get_message = get_message
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-1", cfg, last_event_id=2, heartbeat_secs=0.0)
        out = []
        async for chunk in gen:
            out.append(chunk)
            if len(out) >= 3:
                await gen.aclose()
                break


@pytest.mark.asyncio
async def test_stream_publish_progress_invalid_snapshot():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="{bad json")
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-1", cfg, heartbeat_secs=100)
        first = await gen.__anext__()
        assert "retry" in first
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_publish_progress_error_terminal():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()

    async def get_message(**_kwargs):
        return {
            "type": "message",
            "data": json.dumps({"status": "error", "event_id": 1, "message": "boom"}),
        }

    mock_pubsub.get_message = get_message
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-1", cfg, heartbeat_secs=100)
        chunks = []
        async for chunk in gen:
            chunks.append(chunk)
        assert any("error" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_cleanup_warning():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-1", cfg, heartbeat_secs=0.0)
        async for _ in gen:
            break
        await gen.aclose()


@pytest.mark.asyncio
async def test_get_redis_returns_client():
    cfg = get_settings()
    sse_mod._pool = None
    mock_pool = MagicMock()
    with patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool):
        client = await get_redis(cfg)
    assert client is not None
    sse_mod._pool = None
