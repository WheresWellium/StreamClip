"""Line-coverage sweep for backend/services/sse.py hot-path relay branches
(MASTER_TODO section 3.7 / 3.10)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.services.sse as sse_mod
from backend.services.sse import stream_job_progress, stream_publish_progress
from core.config import get_settings


@pytest.mark.asyncio
async def test_job_stream_emits_heartbeat_then_cleans_up(monkeypatch):
    """341 (heartbeat) + 351-352 (cleanup warning swallowed)."""
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)  # no messages -> heartbeats
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup boom"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-1", cfg, heartbeat_secs=0.0)
        frames: list[str] = []
        async for frame in gen:
            frames.append(frame)
            if any(f.startswith(": heartbeat") for f in frames):
                break
        await gen.aclose()  # triggers finally: unsubscribe raises -> warning (351-352)

    assert any(f.startswith(": heartbeat") for f in frames)


@pytest.mark.asyncio
async def test_publish_stream_cleanup_warning(monkeypatch):
    """247-248: publish relay swallows a pubsub cleanup error."""
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup boom"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pub-1", cfg, heartbeat_secs=100.0)
        async for _ in gen:
            break  # take the retry frame, then close
        await gen.aclose()
