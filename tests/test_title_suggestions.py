"""Tests for core.title_suggestions."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from core.config import get_settings
from core.title_suggestions import (
    _fallback_suggestions,
    generate_title_suggestions,
)


def test_fallback_suggestions_returns_three():
    out = _fallback_suggestions("This is a clutch play in ranked", "gaming")
    assert len(out) == 3
    assert out[0].rank == 1
    assert out[0].title


def test_generate_title_suggestions_parses_llm_json():
    cfg = get_settings()
    payload = {
        "suggestions": [
            {"rank": 1, "title": "Ace clutch", "hook": "Nobody saw this coming", "confidence": 0.9},
            {"rank": 2, "title": "Ranked grind", "hook": "One tap", "confidence": 0.8},
            {"rank": 3, "title": "Insane round", "hook": "Chat exploded", "confidence": 0.7},
        ],
    }
    with patch("core.title_suggestions._call_llm", return_value=json.dumps(payload)):
        with patch("core.title_suggestions._build_client", return_value=MagicMock()):
            out = generate_title_suggestions(
                "we clutched the round",
                {"content_profile": "gaming"},
                cfg,
                tone="gaming",
            )
    assert len(out) == 3
    assert out[0].title == "Ace clutch"


def test_generate_title_suggestions_falls_back_on_llm_failure():
    cfg = get_settings()
    with patch("core.title_suggestions._call_llm", side_effect=RuntimeError("down")):
        with patch("core.title_suggestions._build_client", return_value=MagicMock()):
            out = generate_title_suggestions("hello world transcript", {}, cfg)
    assert len(out) == 3
