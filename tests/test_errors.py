"""Domain error taxonomy tests."""

from __future__ import annotations

from core.errors import (
    IngestError,
    InvalidSourceError,
    LLMUnavailableError,
    NoAudioStreamError,
    StreamClipError,
)


def test_invalid_source_error():
    err = InvalidSourceError("bad url")
    assert err.code == "invalid_source"
    assert err.http_status == 400


def test_ingest_error_code():
    err = IngestError("download failed")
    assert err.code == "ingest_failed"


def test_no_audio_not_retryable():
    err = NoAudioStreamError("silent video")
    assert err.is_retryable is False


def test_llm_unavailable_is_retryable():
    err = LLMUnavailableError("ollama down")
    assert err.is_retryable is True


def test_error_to_dict_shape():
    err = StreamClipError("boom", user_message="Boom")
    d = err.to_dict()
    assert d["code"] == "streamclip_error"
    assert d["message"] == "Boom"
