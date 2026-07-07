"""SSE relay when queue.backend=inprocess (memory progress bus)."""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.services.sse import stream_job_progress, stream_publish_progress
from core.config import get_settings
from core.progress_bus import get_progress_bus, reset_progress_bus


@pytest.fixture(autouse=True)
def _fresh_bus():
    reset_progress_bus()
    yield
    reset_progress_bus()


def _job_channel(cfg, job_id: str) -> str:
    return f"{cfg.redis.pubsub_channel_prefix}{job_id}"


def _publish_channel(cfg, publish_job_id: str) -> str:
    return f"{cfg.redis.publish_pubsub_channel_prefix}{publish_job_id}"


@pytest.fixture
def inprocess_cfg(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    return cfg


@pytest.mark.asyncio
async def test_stream_job_inprocess_snapshot_terminal_done(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _job_channel(cfg, "job-mem-done")
    bus.publish(channel, {"status": "done", "stage": "done", "progress": 1.0})

    chunks = [c async for c in stream_job_progress("job-mem-done", cfg)]
    assert any("event: done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_job_inprocess_snapshot_invalid_json(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _job_channel(cfg, "job-mem-bad")
    bus._snapshots[f"{channel}:latest"] = "not-json"

    gen = stream_job_progress("job-mem-bad", cfg, heartbeat_secs=100)
    await gen.__anext__()  # retry hint
    progress = await gen.__anext__()
    assert "event: progress" in progress
    await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_inprocess_live_terminal(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _job_channel(cfg, "job-mem-live")

    async def publish_later():
        await asyncio.sleep(0.05)
        bus.publish(channel, {"status": "processing", "stage": "transcribe", "progress": 0.5})
        bus.publish(channel, {"status": "done", "stage": "done", "progress": 1.0})

    task = asyncio.create_task(publish_later())
    try:
        chunks = [c async for c in stream_job_progress("job-mem-live", cfg, heartbeat_secs=100)]
    finally:
        await task
    assert any("event: done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_job_inprocess_heartbeat(inprocess_cfg):
    cfg = inprocess_cfg
    gen = stream_job_progress("job-mem-hb", cfg, heartbeat_secs=0.0)
    await gen.__anext__()
    second = await gen.__anext__()
    assert "heartbeat" in second
    await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_inprocess_respects_last_event_id(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _job_channel(cfg, "job-mem-cursor")
    bus.publish(channel, {"status": "processing", "progress": 0.1})
    first_id = json.loads(bus.get_snapshot(channel) or "{}").get("event_id")
    bus.publish(channel, {"status": "done", "progress": 1.0})
    done_id = json.loads(bus.get_snapshot(channel) or "{}").get("event_id")

    chunks = [
        c async for c in stream_job_progress(
            "job-mem-cursor", cfg, last_event_id=first_id, heartbeat_secs=100,
        )
    ]
    assert any(f"id: {done_id}" in c for c in chunks)
    assert not any(f"id: {first_id}" in c and "processing" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_job_inprocess_client_disconnect(inprocess_cfg):
    cfg = inprocess_cfg
    gen = stream_job_progress("job-mem-disc", cfg, heartbeat_secs=100)
    await gen.__anext__()
    await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_inprocess_live_invalid_json(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _job_channel(cfg, "job-mem-live-bad")
    queue = bus.subscribe(channel)

    async def publish_raw():
        await asyncio.sleep(0.05)
        queue.put_nowait("plain-text")
        bus.publish(channel, {"status": "error", "stage": "failed", "progress": 0.0})

    task = asyncio.create_task(publish_raw())
    try:
        chunks = [c async for c in stream_job_progress("job-mem-live-bad", cfg, heartbeat_secs=100)]
    finally:
        await task
    assert any("error" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_inprocess_snapshot_error(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _publish_channel(cfg, "pj-mem-err")
    bus.publish(channel, {"status": "error", "stage": "oauth", "progress": 0.0})

    chunks = [c async for c in stream_publish_progress("pj-mem-err", cfg)]
    assert any("event: error" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_inprocess_live_and_heartbeat(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = _publish_channel(cfg, "pj-mem-live")

    async def publish_later():
        await asyncio.sleep(0.05)
        bus.publish(channel, {"status": "processing", "stage": "upload", "progress": 0.3})
        bus.publish(channel, {"status": "done", "stage": "done", "progress": 1.0})

    task = asyncio.create_task(publish_later())
    try:
        chunks = [c async for c in stream_publish_progress("pj-mem-live", cfg, heartbeat_secs=100)]
    finally:
        await task
    assert any("event: done" in c for c in chunks)

    gen = stream_publish_progress("pj-mem-hb", cfg, heartbeat_secs=0.0)
    await gen.__anext__()
    hb = await gen.__anext__()
    assert "heartbeat" in hb
    await gen.aclose()
