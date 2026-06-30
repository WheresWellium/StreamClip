"""Clip metadata derivation tests."""

from __future__ import annotations

from core.clip_metadata import derive_clip_metadata


def test_derive_from_transcript():
    text = "I'd turn into an exorcism really quick. That was insane."
    title, hook = derive_clip_metadata(text)
    assert title == "I'd turn into an exorcism really quick."
    assert hook == text


def test_derive_truncates_long_hook():
    text = " ".join(["word"] * 50)
    title, hook = derive_clip_metadata(text)
    assert len(hook) <= 180
    assert hook.endswith("…")
    assert len(title.split()) <= 10


def test_derive_empty():
    title, hook = derive_clip_metadata("   ")
    assert title == "Untitled clip"
    assert hook == ""
