"""Twitch chat loader tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.chat_spikes import ChatEvent
from core.config import get_settings
from core.twitch_chat import (
    _events_from_gql_payload,
    _load_cached_chat,
    _save_cached_chat,
    fetch_vod_chat,
    parse_twitch_vod_id,
)


def test_parse_twitch_vod_id():
    assert parse_twitch_vod_id("https://twitch.tv/videos/12345") == "12345"
    assert parse_twitch_vod_id("https://www.twitch.tv/foo/v/99") == "99"
    assert parse_twitch_vod_id(None) is None
    assert parse_twitch_vod_id("https://youtube.com/watch?v=x") is None


def test_events_from_gql_payload():
    data = {
        "data": {
            "video": {
                "comments": {
                    "edges": [
                        {
                            "node": {
                                "contentOffsetSeconds": 1,
                                "message": {"fragments": [{"text": "hi"}]},
                            }
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "cursor": "c"},
                }
            }
        }
    }
    events, cursor, more = _events_from_gql_payload(data)
    assert len(events) == 1
    assert cursor == "c"
    assert more is False


def test_load_cached_chat(tmp_path):
    p = tmp_path / "chat.json"
    assert _load_cached_chat(p) == []
    p.write_text("not json", encoding="utf-8")
    assert _load_cached_chat(p) == []
    p.write_text(json.dumps([{"offset_secs": 1, "text": "a"}]), encoding="utf-8")
    ev = _load_cached_chat(p)
    assert ev[0].text == "a"


def test_save_cached_chat(tmp_path):
    p = tmp_path / "sub/chat.json"
    _save_cached_chat(p, [ChatEvent(0.0, "x")])
    assert p.exists()


def test_fetch_from_cache(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps([{"t": 2, "message": "m"}]), encoding="utf-8")
    cfg = get_settings()
    out = fetch_vod_chat(source_url="https://twitch.tv/videos/1", cfg=cfg, cache_path=p)
    assert len(out) == 1


def test_fetch_no_client_id():
    cfg = get_settings(reload=True)
    cfg.twitch_client_id = ""
    assert fetch_vod_chat(source_url="https://twitch.tv/videos/1", cfg=cfg) == []


def test_fetch_gql_success():
    cfg = get_settings(reload=True)
    cfg.twitch_client_id = "cid"
    payload = {
        "data": {
            "video": {
                "comments": {
                    "edges": [
                        {
                            "node": {
                                "contentOffsetSeconds": 0,
                                "message": {"fragments": [{"text": "yo"}]},
                            }
                        }
                    ],
                    "pageInfo": {"hasNextPage": False},
                }
            }
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = payload
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client
    mock_cm.__exit__.return_value = None
    with patch("core.twitch_chat.httpx.Client", return_value=mock_cm):
        events = fetch_vod_chat(source_url="https://twitch.tv/videos/42",
            cfg=cfg,
            cache_path=Path("/tmp/none.json"),
        )
    assert events[0].text == "yo"


def test_fetch_gql_failure():
    cfg = get_settings(reload=True)
    cfg.twitch_client_id = "cid"
    with patch("core.twitch_chat.httpx.Client", side_effect=RuntimeError("net")):
        assert fetch_vod_chat(source_url="https://twitch.tv/videos/1", cfg=cfg) == []

