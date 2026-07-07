"""
In-process progress bus — Redis-compatible snapshot + pub/sub for desktop mode (ADR-001 §4.2).

When ``queue.backend=inprocess``, ``publish_progress`` / SSE relay use this module
instead of Redis so a single-machine .exe needs no broker.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import defaultdict
from typing import Any

import structlog

from core.config import Settings, get_settings

log = structlog.get_logger(__name__)

_lock = threading.Lock()
_bus: MemoryProgressBus | None = None


class MemoryKVStore:
    """Minimal Redis-like KV store for progress timing (get/set/incr)."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._counters: dict[str, int] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:  # noqa: ARG002
        with self._lock:
            self._data[key] = value

    def incr(self, key: str) -> int:
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1
            return self._counters[key]

    def expire(self, key: str, secs: int) -> None:  # noqa: ARG002
        return


class MemoryProgressBus:
    """Thread-safe in-memory pub/sub with snapshot + monotonic event ids."""

    def __init__(self, cfg: Settings) -> None:
        self._cfg = cfg
        self._kv = MemoryKVStore()
        self._snapshots: dict[str, str] = {}
        self._seq: dict[str, int] = {}
        self._async_subscribers: dict[str, list[asyncio.Queue[str]]] = defaultdict(list)
        self._lock = threading.Lock()

    @property
    def kv(self) -> MemoryKVStore:
        return self._kv

    def _channel_keys(self, channel: str) -> tuple[str, str]:
        snapshot_key = f"{channel}:latest"
        seq_key = f"{channel}:seq"
        return snapshot_key, seq_key

    def publish(self, channel: str, payload: dict[str, Any]) -> int:
        """Publish payload; return assigned event_id."""
        _, seq_key = self._channel_keys(channel)
        snapshot_key = f"{channel}:latest"

        with self._lock:
            event_id = self._seq.get(seq_key, 0) + 1
            self._seq[seq_key] = event_id
            payload = {**payload, "event_id": event_id}
            blob = json.dumps(payload)
            self._snapshots[snapshot_key] = blob
            queues = list(self._async_subscribers.get(channel, []))

        for q in queues:
            try:
                q.put_nowait(blob)
            except asyncio.QueueFull:
                log.warning("progress_bus_queue_full", channel=channel)

        return event_id

    def get_snapshot(self, channel: str) -> str | None:
        snapshot_key = f"{channel}:latest"
        with self._lock:
            return self._snapshots.get(snapshot_key)

    def subscribe(self, channel: str) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        with self._lock:
            self._async_subscribers[channel].append(q)
        return q

    def unsubscribe(self, channel: str, queue: asyncio.Queue[str]) -> None:
        with self._lock:
            subs = self._async_subscribers.get(channel, [])
            if queue in subs:
                subs.remove(queue)


def get_progress_bus(cfg: Settings | None = None) -> MemoryProgressBus:
    global _bus
    if _bus is None:
        with _lock:
            if _bus is None:
                _bus = MemoryProgressBus(cfg or get_settings())
    return _bus


def reset_progress_bus() -> None:
    """Test helper — drop the singleton bus."""
    global _bus
    with _lock:
        _bus = None


def publish_job_channel(
    cfg: Settings,
    job_id: str,
    *,
    stage: str,
    progress: float,
    message: str = "",
    status: str = "processing",
    extra: dict[str, Any] | None = None,
    timing_fields: dict[str, Any] | None = None,
) -> None:
    channel = f"{cfg.redis.pubsub_channel_prefix}{job_id}"
    payload: dict[str, Any] = {
        "job_id": job_id,
        "stage": stage,
        "progress": round(max(0.0, min(1.0, progress)), 4),
        "message": message,
        "status": status,
        "ts": time.time(),
        **(timing_fields or {}),
    }
    if extra:
        payload["extra"] = extra
    get_progress_bus(cfg).publish(channel, payload)


def publish_publish_channel(
    cfg: Settings,
    publish_job_id: str,
    *,
    stage: str,
    progress: float,
    message: str = "",
    status: str = "processing",
    extra: dict[str, Any] | None = None,
) -> None:
    prefix = cfg.redis.publish_pubsub_channel_prefix
    channel = f"{prefix}{publish_job_id}"
    payload: dict[str, Any] = {
        "publish_job_id": publish_job_id,
        "stage": stage,
        "progress": round(max(0.0, min(1.0, progress)), 4),
        "message": message,
        "status": status,
        "ts": time.time(),
        **(extra or {}),
    }
    get_progress_bus(cfg).publish(channel, payload)
