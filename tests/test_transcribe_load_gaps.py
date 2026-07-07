"""Additional transcribe paths: storage download, subtitle seed, load failures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import get_settings
from core.models import Transcript, TranscriptSegment, Word
from core import transcribe as tr


def _sample(path: Path) -> Transcript:
    w = Word(text="wow", start=0.0, end=0.4, probability=0.9)
    seg = TranscriptSegment(id=0, text="wow", start=0.0, end=1.0, words=(w,))
    return Transcript(segments=[seg], language="en", duration=1.0, source_path=path)


def test_load_job_transcript_raises_without_fallback(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    with pytest.raises(FileNotFoundError):
        tr.load_job_transcript("missing-job", cfg, fallback_transcribe=False)


def test_load_job_transcript_downloads_from_storage(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    storage = MagicMock()
    storage.exists.return_value = True

    def _download(key, dest, on_progress=None):
        tr._save_transcript(_sample(tmp_path / "v.mp4"), dest)

    storage.download.side_effect = _download
    out = tr.load_job_transcript("job-dl", cfg, storage=storage)
    assert out.segments[0].text == "wow"


def test_transcribe_subtitle_seed(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"x")
    srt = tmp_path / "subs.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nworld\n\n"
        "3\n00:00:02,000 --> 00:00:03,000\nagain\n",
        encoding="utf-8",
    )
    out = tr.transcribe(vid, cfg, subtitle_path=srt)
    assert len(out.segments) >= 3


def test_parse_segments_with_words():
    cfg = get_settings()
    seg = MagicMock(
        text=" hello ",
        start=0.0,
        end=1.0,
        words=[MagicMock(word=" hi ", start=0.1, end=0.5, probability=0.8)],
    )
    parsed = tr._parse_segments(iter([seg]), cfg.whisper)
    assert parsed[0].words[0].text == "hi"


def test_video_hash_samples_file_tail(tmp_path):
    big = tmp_path / "big.bin"
    chunk = 3 << 20
    with open(big, "wb") as fh:
        fh.write(b"a" * chunk)
        fh.write(b"b" * chunk)
    digest = tr._video_hash(big)
    assert len(digest) == 20


def test_load_job_transcript_fallback_transcribe(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    job_id = "job-fallback"
    ws = tmp_path / "jobs" / job_id
    ws.mkdir(parents=True)
    src = ws / "source.mp4"
    src.write_bytes(b"video")
    storage = MagicMock()
    storage.exists.return_value = False
    sample = _sample(src)
    with patch("core.ingest.service.get_job_source_path", return_value=src), \
         patch.object(tr, "transcribe", return_value=sample) as transcribe:
        out = tr.load_job_transcript(job_id, cfg, storage=storage)
    assert out.segments[0].text == "wow"
    transcribe.assert_called_once_with(src, cfg)


def test_load_job_transcript_missing_source_raises(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    storage = MagicMock()
    storage.exists.return_value = False
    missing = tmp_path / "missing.mp4"
    with patch("core.ingest.service.get_job_source_path", return_value=missing):
        with pytest.raises(FileNotFoundError, match="No transcript or source"):
            tr.load_job_transcript("job-x", cfg, storage=storage)
