"""
StreamClip — Server-Sent Events Relay

Bridges Redis pub/sub → SSE for live job progress in the browser.

Why SSE and not WebSockets:
  • Progress is one-way (server → client). WS bidirectionality is unused.
  • SSE auto-reconnects via `Last-Event-Id`. Browsers handle this for free.
  • Works over plain HTTPS through every proxy and CDN — no Upgrade dance.
  • In tRPC v11 the subscriptions API can use SSE as transport — same pattern
    is now the default recommendation.

The relay:
  1. Sends the cached snapshot (so reconnects don't blank-screen the UI).
  2. Subscribes to the job's Redis channel.
  3. Yields events as they arrive, with a heartbeat every 15s to keep
     intermediate proxies from timing out the connection.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
import structlog

from core.config import Settings

log = structlog.get_logger(__name__)


# ─── Connection helper ───────────────────────────────────────────────────────

_pool: aioredis.ConnectionPool | None = None


def _get_pool(cfg: Settings) -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            cfg.redis.url,
            max_connections=cfg.redis.max_connections,
            decode_responses=True,
        )
    return _pool


async def get_redis(cfg: Settings) -> aioredis.Redis:
    return aioredis.Redis(connection_pool=_get_pool(cfg))


# ─── SSE event formatter ─────────────────────────────────────────────────────

def _format_sse(data: str, *, event: str | None = None, retry: int | None = None) -> str:
    """Format a payload as an SSE wire-format frame."""
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    if retry:
        lines.append(f"retry: {retry}")
    # Each data line must be prefixed; multi-line strings need each line tagged
    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


# ─── Main relay generator ────────────────────────────────────────────────────

async def stream_job_progress(
    job_id: str,
    cfg: Settings,
    *,
    heartbeat_secs: float = 15.0,
) -> AsyncGenerator[str, None]:
    """
    Async generator yielding SSE-formatted strings for a single job.
    Closes when the job emits `status: done` or `status: error`,
    or when the client disconnects (caller will cancel the generator).
    """
    r = await get_redis(cfg)
    channel = f"{cfg.redis.pubsub_channel_prefix}{job_id}"
    snapshot_key = f"{channel}:latest"

    # ── 1. Send retry hint and the cached snapshot ─────────────────────────
    yield _format_sse("", retry=3000)

    snapshot = await r.get(snapshot_key)
    if snapshot:
        yield _format_sse(snapshot, event="progress")
        try:
            data = json.loads(snapshot)
            if data.get("status") in ("done", "error"):
                # Job already finished — close the stream
                yield _format_sse(snapshot, event=data["status"])
                return
        except json.JSONDecodeError:
            pass

    # ── 2. Subscribe to the live channel ──────────────────────────────────
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    log.info("sse_subscribed", channel=channel)

    try:
        last_heartbeat = asyncio.get_running_loop().time()
        while True:
            # Non-blocking read with timeout
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            now = asyncio.get_running_loop().time()
            if message and message.get("type") == "message":
                payload: str = message["data"]
                try:
                    data = json.loads(payload)
                    status = data.get("status", "processing")
                except json.JSONDecodeError:
                    status = "processing"

                yield _format_sse(payload, event="progress")

                # Terminal event — emit final event and close
                if status in ("done", "error"):
                    yield _format_sse(payload, event=status)
                    log.info("sse_terminated", channel=channel, status=status)
                    return
                last_heartbeat = now

            elif now - last_heartbeat >= heartbeat_secs:
                # Heartbeat keeps proxies awake. SSE comment lines (`:`)
                # are ignored by the EventSource client.
                yield f": heartbeat {int(now)}\n\n"
                last_heartbeat = now

    except asyncio.CancelledError:
        # Client disconnected
        log.info("sse_client_disconnected", channel=channel)
        raise
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception as exc:
            log.warning("sse_cleanup_error", error=str(exc))
