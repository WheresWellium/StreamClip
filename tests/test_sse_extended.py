"""SSE stream tests."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import sse as sse_mod
from backend.services.sse import _format_sse, stream_job_progress
from core.config import get_settings


def test_format_sse_multiline_and_retry():
    frame = _format_sse("a\nb", event="e", event_id=1, retry=1000)
    assert "retry: 1000" in frame
    assert "data: a" in frame and "data: b" in frame


@pytest.mark.asyncio
async def test_stream_job_progress_snapshot_terminal():
    cfg = get_settings()
    snapshot = json.dumps({"status": "done", "event_id": 1, "stage": "x"})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=snapshot)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job1", cfg, heartbeat_secs=0.01)
        chunks = []
        try:
            async for c in gen:
                chunks.append(c)
                if len(chunks) > 5:
                    break
        except asyncio.CancelledError:
            pass
    assert any("progress" in c or "done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_live_message_and_heartbeat():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    payloads = [
        {"type": "message", "data": json.dumps({"status": "processing", "event_id": 2})},
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
        gen = stream_job_progress("job1", cfg, last_event_id=1, heartbeat_secs=0.0)
        out = []
        async for chunk in gen:
            out.append(chunk)
            if len(out) >= 3:
                await gen.aclose()
                break


@pytest.mark.asyncio
async def test_stream_invalid_snapshot_json():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="not-json")
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("j", cfg, heartbeat_secs=100)
        first = await gen.__anext__()
        assert "retry" in first
        await gen.aclose()


@pytest.mark.asyncio
async def test_get_pool_cached():
    cfg = get_settings()
    sse_mod._pool = None
    with patch("redis.asyncio.ConnectionPool.from_url") as fp:
        fp.return_value = MagicMock()
        p1 = sse_mod._get_pool(cfg)
        p2 = sse_mod._get_pool(cfg)
        assert p1 is p2
    sse_mod._pool = None
