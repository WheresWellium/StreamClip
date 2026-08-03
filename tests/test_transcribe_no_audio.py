"""Transcription must fail cleanly on video-only media (no Whisper crash)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.errors import NoAudioStreamError
from core.transcribe import _ensure_audio_stream, _media_has_audio_stream, transcribe


def test_media_has_audio_stream_false_for_video_only(tmp_path, monkeypatch):
    vid = tmp_path / "silent.mp4"
    vid.write_bytes(b"x")

    def fake_run(cmd, capture_output=True, text=True, check=False):
        return MagicMock(returncode=0, stdout='{"streams": []}')

    monkeypatch.setattr("core.transcribe.subprocess.run", fake_run)
    monkeypatch.setattr("core.transcribe.ffprobe_bin", lambda: "ffprobe")
    assert _media_has_audio_stream(vid) is False


def test_ensure_audio_stream_raises_no_audio(tmp_path, monkeypatch):
    vid = tmp_path / "silent.mp4"
    vid.write_bytes(b"x")
    monkeypatch.setattr("core.transcribe._media_has_audio_stream", lambda _p: False)
    with pytest.raises(NoAudioStreamError) as ei:
        _ensure_audio_stream(vid)
    assert ei.value.code == "no_audio_stream"
    assert "no audio" in ei.value.user_message.lower()


def test_transcribe_maps_pyav_index_error(tmp_path, monkeypatch):
    vid = tmp_path / "bad.mp4"
    vid.write_bytes(b"x")
    cfg = MagicMock()
    cfg.whisper.model_size = "tiny"
    cfg.whisper.language = None
    cfg.whisper.word_timestamps = True
    cfg.whisper.beam_size = 1
    cfg.whisper.vad_filter = False
    cfg.cache_dir = tmp_path

    monkeypatch.setattr("core.transcribe._media_has_audio_stream", lambda _p: True)
    monkeypatch.setattr("core.transcribe._cache_path", lambda *_a, **_k: tmp_path / "no.json")

    model = MagicMock()
    model.transcribe.side_effect = IndexError("tuple index out of range")
    monkeypatch.setattr("core.transcribe._get_model", lambda _c: model)

    with pytest.raises(NoAudioStreamError):
        transcribe(vid, cfg, force=True)
