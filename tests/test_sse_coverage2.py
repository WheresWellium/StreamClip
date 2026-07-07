"""SSE relay edge cases for 110% coverage."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import sse as sse_mod
from backend.services.sse import stream_job_progress, stream_publish_progress
from core.config import get_settings


@pytest.mark.asyncio
async def test_stream_job_snapshot_terminal_done():
    cfg = get_settings()
    snapshot = json.dumps({"status": "done", "event_id": 5})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=snapshot)
    mock_pubsub = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        chunks = [c async for c in stream_job_progress("job-1", cfg)]
    assert any("done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_job_snapshot_invalid_json():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="not-json")
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-1", cfg, heartbeat_secs=0.0)
        first = await gen.__anext__()
        assert "progress" in first or first.startswith("retry:")
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_heartbeat():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-1", cfg, heartbeat_secs=0.0)
        await gen.__anext__()
        second = await gen.__anext__()
        assert "heartbeat" in second
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_skips_old_events():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    calls = 0

    async def get_message(**_kwargs):
        nonlocal calls
        calls += 1
        if calls >= 2:
            return {
                "type": "message",
                "data": json.dumps({"status": "done", "event_id": 100}),
            }
        return {
            "type": "message",
            "data": json.dumps({"status": "processing", "event_id": 1}),
        }

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = get_message
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        chunks = [c async for c in stream_job_progress("job-1", cfg, last_event_id=99)]
    assert any("done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_snapshot_error():
    cfg = get_settings()
    snapshot = json.dumps({"status": "error", "event_id": 2})
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=snapshot)
    mock_pubsub = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        chunks = [c async for c in stream_publish_progress("pj-1", cfg)]
    assert any("error" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_live_invalid_json():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    calls = 0

    async def get_message(**_kwargs):
        nonlocal calls
        calls += 1
        if calls >= 2:
            return {
                "type": "message",
                "data": json.dumps({"status": "done", "event_id": 1}),
            }
        return {"type": "message", "data": "plain-text"}

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = get_message
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        chunks = [c async for c in stream_publish_progress("pj-1", cfg)]
    assert chunks


@pytest.mark.asyncio
async def test_stream_publish_cleanup_warning():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("fail"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-1", cfg, heartbeat_secs=0.0)
        await gen.__anext__()
        await gen.aclose()
