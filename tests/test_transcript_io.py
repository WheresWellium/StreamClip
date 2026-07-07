"""Coverage for core.transcript_io — load/save without faster-whisper."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.config import get_settings
from core.models import Transcript, TranscriptSegment, Word
from core.transcript_io import (
    load_persisted_job_transcript,
    load_transcript,
    save_transcript,
)


def _sample_transcript(path: Path) -> Transcript:
    return Transcript(
        segments=(
            TranscriptSegment(
                id=0,
                text="hello world",
                start=0.0,
                end=1.5,
                speaker=None,
                words=(
                    Word(text="hello", start=0.0, end=0.6, probability=0.9),
                    Word(text="world", start=0.6, end=1.5, probability=0.85),
                ),
            ),
        ),
        language="en",
        duration=1.5,
        source_path=path,
    )


def test_save_and_load_transcript_roundtrip(tmp_path: Path):
    src = tmp_path / "source.mp4"
    path = tmp_path / "transcript.json"
    original = _sample_transcript(src)
    save_transcript(original, path)

    loaded = load_transcript(path)
    assert loaded.language == "en"
    assert len(loaded.segments) == 1
    assert loaded.segments[0].words[1].text == "world"


def test_load_persisted_job_transcript_from_workspace(tmp_path: Path):
    cfg = get_settings()
    old_ws = cfg.workspace_dir
    job_id = "job-local-tx"
    try:
        cfg.workspace_dir = tmp_path
        job_dir = tmp_path / "jobs" / job_id
        job_dir.mkdir(parents=True)
        src = job_dir / "source.mp4"
        save_transcript(_sample_transcript(src), job_dir / "transcript.json")

        storage = MagicMock()
        storage.exists.return_value = False

        loaded = load_persisted_job_transcript(job_id, cfg, storage)
        assert loaded.duration == 1.5
        storage.download.assert_not_called()
    finally:
        cfg.workspace_dir = old_ws


def test_load_persisted_job_transcript_downloads_from_storage(tmp_path: Path):
    cfg = get_settings()
    old_ws = cfg.workspace_dir
    job_id = "job-remote-tx"
    try:
        cfg.workspace_dir = tmp_path
        storage = MagicMock()
        storage.exists.return_value = True

        def fake_download(key: str, dest: Path) -> None:
            save_transcript(_sample_transcript(tmp_path / "source.mp4"), dest)

        storage.download.side_effect = fake_download

        loaded = load_persisted_job_transcript(job_id, cfg, storage)
        assert loaded.segments[0].text == "hello world"
        storage.download.assert_called_once()
    finally:
        cfg.workspace_dir = old_ws


def test_load_persisted_job_transcript_missing_raises(tmp_path: Path):
    cfg = get_settings()
    old_ws = cfg.workspace_dir
    try:
        cfg.workspace_dir = tmp_path
        storage = MagicMock()
        storage.exists.return_value = False
        with pytest.raises(FileNotFoundError, match="No persisted transcript"):
            load_persisted_job_transcript("missing-job", cfg, storage)
    finally:
        cfg.workspace_dir = old_ws
