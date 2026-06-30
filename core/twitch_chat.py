"""
StreamClip — Twitch VOD chat loader

Fetches replay chat for Twitch VOD URLs via the public GQL API when
``twitch_client_id`` is configured. Falls back to a job-local ``chat.json``
cache when present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import structlog

from core.chat_spikes import ChatEvent
from core.config import Settings

log = structlog.get_logger(__name__)

_TWITCH_VOD_RE = re.compile(
    r"(?:twitch\.tv/videos/|twitch\.tv/\w+/v/)(\d+)",
    re.IGNORECASE,
)

_GQL_URL = "https://gql.twitch.tv/gql"
_GQL_QUERY = """
query VideoCommentsByOffsetOrCursor($videoID: ID!, $cursor: String, $contentOffsetSeconds: Int) {
  video(id: $videoID) {
    comments(contentOffsetSeconds: $contentOffsetSeconds, cursor: $cursor) {
      edges {
        cursor
        node {
          contentOffsetSeconds
          message {
            fragments { text }
          }
        }
      }
      pageInfo { hasNextPage cursor }
    }
  }
}
"""


def parse_twitch_vod_id(source_url: str | None) -> str | None:
    if not source_url:
        return None
    m = _TWITCH_VOD_RE.search(source_url)
    return m.group(1) if m else None


def _events_from_gql_payload(data: dict[str, Any]) -> tuple[list[ChatEvent], str | None, bool]:
    video = (data.get("data") or {}).get("video") or {}
    comments = video.get("comments") or {}
    edges = comments.get("edges") or []
    events: list[ChatEvent] = []
    for edge in edges:
        node = edge.get("node") or {}
        offset = float(node.get("contentOffsetSeconds") or 0)
        fragments = ((node.get("message") or {}).get("fragments")) or []
        text = "".join(f.get("text", "") for f in fragments).strip()
        if text:
            events.append(ChatEvent(offset_secs=offset, text=text))
    page = comments.get("pageInfo") or {}
    return events, page.get("cursor"), bool(page.get("hasNextPage"))


def _load_cached_chat(cache_path: Path) -> list[ChatEvent]:
    if not cache_path.exists():
        return []
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("chat_cache_read_failed", path=str(cache_path), error=str(exc))
        return []
    events: list[ChatEvent] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        events.append(
            ChatEvent(
                offset_secs=float(item.get("offset_secs", item.get("t", 0))),
                text=str(item.get("text", item.get("message", ""))),
            )
        )
    return events


def _save_cached_chat(cache_path: Path, events: list[ChatEvent]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"offset_secs": e.offset_secs, "text": e.text} for e in events]
    cache_path.write_text(json.dumps(payload), encoding="utf-8")


def fetch_vod_chat(
    *,
    source_url: str | None,
    cfg: Settings,
    cache_path: Path | None = None,
    max_messages: int = 5000,
) -> list[ChatEvent]:
    """
    Load chat events for a Twitch VOD.

    Order: job cache file → live GQL fetch (cached on success) → empty list.
    """
    if cache_path and cache_path.exists():
        cached = _load_cached_chat(cache_path)
        if cached:
            log.info("chat_loaded_from_cache", count=len(cached))
            return cached

    vod_id = parse_twitch_vod_id(source_url)
    if not vod_id or not cfg.twitch_client_id:
        return []

    headers = {
        "Client-ID": cfg.twitch_client_id,
        "Content-Type": "application/json",
    }
    events: list[ChatEvent] = []
    cursor: str | None = None
    offset = 0

    try:
        with httpx.Client(timeout=30.0) as client:
            while len(events) < max_messages:
                variables: dict[str, Any] = {
                    "videoID": vod_id,
                    "contentOffsetSeconds": offset,
                }
                if cursor:
                    variables["cursor"] = cursor
                resp = client.post(
                    _GQL_URL,
                    headers=headers,
                    json={
                        "operationName": "VideoCommentsByOffsetOrCursor",
                        "query": _GQL_QUERY,
                        "variables": variables,
                    },
                )
                resp.raise_for_status()
                batch, cursor, has_more = _events_from_gql_payload(resp.json())
                if not batch:
                    break
                events.extend(batch)
                offset = int(batch[-1].offset_secs)
                if not has_more:
                    break
    except Exception as exc:
        log.warning("twitch_chat_fetch_failed", vod_id=vod_id, error=str(exc))
        return []

    log.info("twitch_chat_fetched", vod_id=vod_id, count=len(events))
    if cache_path and events:
        _save_cached_chat(cache_path, events)
    return events[:max_messages]
