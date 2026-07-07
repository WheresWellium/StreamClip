"""Remaining stream_job_progress paths."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import sse as sse_mod
from backend.services.sse import stream_job_progress
from core.config import get_settings


@pytest.mark.asyncio
async def test_stream_job_progress_error_terminal():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()

    async def get_message(**_kwargs):
        return {
            "type": "message",
            "data": json.dumps({"status": "error", "event_id": 1}),
        }

    mock_pubsub.get_message = get_message
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-1", cfg, heartbeat_secs=100)
        chunks = []
        async for chunk in gen:
            chunks.append(chunk)
        assert any("error" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_job_progress_cleanup_warning():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-1", cfg, heartbeat_secs=0.0)
        async for _ in gen:
            break
        await gen.aclose()
