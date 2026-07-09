"""Unit tests for in-memory progress bus (ADR-001 §4.2)."""

from __future__ import annotations

import asyncio

import pytest

from core.config import get_settings
from core.progress_bus import (
    MemoryKVStore,
    MemoryProgressBus,
    get_progress_bus,
    publish_job_channel,
    publish_publish_channel,
    reset_progress_bus,
)


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_progress_bus()
    yield
    reset_progress_bus()


def test_memory_kv_get_set_incr():
    kv = MemoryKVStore()
    assert kv.get("missing") is None
    kv.set("k", "v", ex=10)
    assert kv.get("k") == "v"
    assert kv.incr("c") == 1
    assert kv.incr("c") == 2
    kv.expire("k", 5)  # no-op


def test_progress_bus_publish_and_snapshot():
    cfg = get_settings(reload=True)
    bus = MemoryProgressBus(cfg)
    eid = bus.publish("ch1", {"stage": "ingesting", "progress": 0.1})
    assert eid == 1
    snap = bus.get_snapshot("ch1")
    assert snap is not None
    assert "ingesting" in snap
    assert bus.publish("ch1", {"stage": "done", "progress": 1.0}) == 2


@pytest.mark.asyncio
async def test_progress_bus_subscribe_receives_events():
    cfg = get_settings(reload=True)
    bus = MemoryProgressBus(cfg)
    q = bus.subscribe("live")
    bus.publish("live", {"stage": "a", "progress": 0.2})
    blob = await asyncio.wait_for(q.get(), timeout=1)
    assert "a" in blob
    bus.unsubscribe("live", q)
    bus.publish("live", {"stage": "b", "progress": 0.5})
    assert q.empty()


def test_publish_job_and_publish_channels():
    cfg = get_settings(reload=True)
    publish_job_channel(
        cfg,
        "job-1",
        stage="transcribe",
        progress=1.5,
        message="ok",
        extra={"clips": 2},
        timing_fields={"elapsed_s": 1.2},
    )
    bus = get_progress_bus(cfg)
    job_ch = f"{cfg.redis.pubsub_channel_prefix}job-1"
    snap = bus.get_snapshot(job_ch)
    assert snap is not None
    assert "transcribe" in snap
    assert '"progress": 1.0' in snap or '"progress":1.0' in snap.replace(" ", "")

    publish_publish_channel(
        cfg,
        "pj-9",
        stage="uploading",
        progress=-0.1,
        message="start",
        extra={"platform": "youtube_shorts"},
    )
    pub_ch = f"{cfg.redis.publish_pubsub_channel_prefix}pj-9"
    pub_snap = bus.get_snapshot(pub_ch)
    assert pub_snap is not None
    assert "uploading" in pub_snap
    assert '"progress": 0.0' in pub_snap or '"progress":0.0' in pub_snap.replace(" ", "")


def test_get_progress_bus_is_singleton():
    cfg = get_settings(reload=True)
    assert get_progress_bus(cfg) is get_progress_bus(cfg)
