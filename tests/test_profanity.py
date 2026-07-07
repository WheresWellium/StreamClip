"""Profanity filter and transcript-edit tests (Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.api.schemas import CreateJobRequest, UpdateClipRequest
from core.captions import apply_transcript_edits
from core.models import Word
from core.profanity import (
    censor_text,
    censor_token,
    censor_words,
    default_wordlist_path,
    is_profane,
    load_profanity_words,
)


def _w(text: str, start: float = 0.0, end: float = 0.5) -> Word:
    return Word(text=text, start=start, end=end, probability=0.9)


# ─── Wordlist loading ─────────────────────────────────────────────────────────

def test_default_wordlist_exists_and_loads():
    path = default_wordlist_path()
    assert path.exists()
    words = load_profanity_words()
    assert "fuck" in words
    assert "shit" in words
    # Comments and blank lines are ignored
    assert not any(w.startswith("#") for w in words)


def test_missing_wordlist_falls_back_to_builtin(tmp_path: Path):
    words = load_profanity_words(tmp_path / "nope.txt")
    assert "fuck" in words


def test_custom_wordlist(tmp_path: Path):
    custom = tmp_path / "custom.txt"
    custom.write_text("# my list\nfoo\nbar\n", encoding="utf-8")
    words = load_profanity_words(custom)
    assert words == frozenset({"foo", "bar"})


# ─── Detection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("token", ["fuck", "FUCK", "Fuck!", "$hit", "sh1t", "shit,"])
def test_is_profane_variants(token: str):
    assert is_profane(token)


@pytest.mark.parametrize("token", ["duck", "ship", "hello", "", "clutch"])
def test_is_not_profane(token: str):
    assert not is_profane(token)


# ─── Censoring modes ──────────────────────────────────────────────────────────

def test_censor_token_mask():
    assert censor_token("fuck", "mask") == "f***"
    # Punctuation preserved around the masked core
    assert censor_token("fuck!", "mask") == "f***!"


def test_censor_token_bleep():
    assert censor_token("shit", "bleep") == "•••"


def test_censor_token_omit():
    assert censor_token("shit", "omit") is None


def test_censor_words_mask_preserves_timing():
    words = [_w("that"), _w("fucking", 0.5, 1.0), _w("play", 1.0, 1.5)]
    result = censor_words(words, "mask")
    assert len(result) == 3
    assert result[1].text == "f******"
    assert result[1].start == 0.5 and result[1].end == 1.0
    assert result[0].text == "that" and result[2].text == "play"


def test_censor_words_omit_drops_word():
    words = [_w("what"), _w("the", 0.5, 1.0), _w("fuck", 1.0, 1.5)]
    result = censor_words(words, "omit")
    assert [w.text for w in result] == ["what", "the"]


def test_censor_text_modes():
    text = "what the fuck was that"
    assert censor_text(text, "mask") == "what the f*** was that"
    assert censor_text(text, "bleep") == "what the ••• was that"
    assert censor_text(text, "omit") == "what the was that"
    assert censor_text("", "mask") == ""
    assert censor_text("clean sentence here", "mask") == "clean sentence here"


# ─── Transcript edits (Phase 2b-i) ────────────────────────────────────────────

def test_apply_transcript_edits_replaces_and_removes():
    words = [_w("teh"), _w("clutch", 0.5, 1.0), _w("umm", 1.0, 1.5)]
    edited = apply_transcript_edits(words, {"0": "the", "2": ""})
    assert [w.text for w in edited] == ["the", "clutch"]
    # Timing untouched
    assert edited[0].start == 0.0 and edited[0].end == 0.5


def test_apply_transcript_edits_ignores_out_of_range_and_noop():
    words = [_w("hello")]
    assert apply_transcript_edits(words, None) is words
    assert apply_transcript_edits(words, {}) is words
    edited = apply_transcript_edits(words, {"99": "world"})
    assert [w.text for w in edited] == ["hello"]


# ─── API schema validation ────────────────────────────────────────────────────

def test_update_clip_request_accepts_transcript_edits():
    req = UpdateClipRequest(transcript_edits={"0": "hello", "3": ""})
    assert req.transcript_edits == {"0": "hello", "3": ""}


def test_update_clip_request_rejects_non_numeric_keys():
    with pytest.raises(ValidationError):
        UpdateClipRequest(transcript_edits={"abc": "hello"})


def test_update_clip_request_rejects_oversized_edit():
    with pytest.raises(ValidationError):
        UpdateClipRequest(transcript_edits={"0": "x" * 81})


def test_create_job_request_profanity_defaults():
    req = CreateJobRequest(source_url="https://www.twitch.tv/videos/123")
    assert req.profanity_filter is False
    assert req.profanity_mode == "mask"


def test_create_job_request_profanity_mode_validated():
    req = CreateJobRequest(
        source_url="https://www.twitch.tv/videos/123",
        profanity_filter=True,
        profanity_mode="bleep",
    )
    assert req.profanity_filter is True
    assert req.profanity_mode == "bleep"
    with pytest.raises(ValidationError):
        CreateJobRequest(
            source_url="https://www.twitch.tv/videos/123",
            profanity_mode="blur",
        )
