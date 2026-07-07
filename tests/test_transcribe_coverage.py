"""Transcribe module coverage with mocked Whisper."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from core.config import get_settings
from core.models import Transcript, TranscriptSegment, Word
from core import transcribe as tr

def _sample_transcript(path: Path) -> Transcript:
    w = Word(text="hi", start=0.0, end=0.5, probability=0.9)
    seg = TranscriptSegment(id=0, text="hi", start=0.0, end=1.0, words=(w,))
    return Transcript(segments=[seg], language="en", duration=1.0, source_path=path)

def test_video_hash_large_file(tmp_path):
    p = tmp_path / "big.bin"
    p.write_bytes(b"a" * (3 * 1024 * 1024))
    assert len(tr._video_hash(p)) == 20

def test_cache_roundtrip(tmp_path):
    t = _sample_transcript(tmp_path / "v.mp4")
    cp = tmp_path / "c.json"
    tr._save_transcript(t, cp)
    assert tr._load_transcript(cp).segments[0].text == "hi"
    tr.save_transcript_json(t, cp)
    tr.export_srt(t, tmp_path / "out.srt")
    tr.export_word_level_json(t, tmp_path / "w.json")

def test_transcribe_cache_hit(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"x")
    cp = tr._cache_path(vid, tmp_path, cfg.whisper.model_size)
    tr._save_transcript(_sample_transcript(vid), cp)
    assert tr.transcribe(vid, cfg).duration == 1.0

def test_transcribe_and_clip_mock_model(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    vid = tmp_path / "v2.mp4"
    vid.write_bytes(b"y")
    seg = TranscriptSegment(id=0, text="a", start=0.0, end=1.0, words=())
    info = MagicMock(language="en", duration=2.0)
    model = MagicMock()
    model.transcribe.return_value = (iter([]), info)
    with patch.object(tr, "_get_model", return_value=model):
        with patch.object(tr, "_parse_segments", return_value=[seg]):
            out = tr.transcribe(vid, cfg, force=True)
            assert out.duration == 2.0
            clip_out = tr.transcribe_clip(vid, cfg)
            assert clip_out.language == "en"

def test_load_job_transcript_paths(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    job_ws = tmp_path / "jobs" / "job1"
    job_ws.mkdir(parents=True)
    local = job_ws / "transcript.json"
    tr._save_transcript(_sample_transcript(tmp_path / "v.mp4"), local)
    assert tr.load_job_transcript("job1", cfg).segments

def test_get_model_cached():
    cfg = get_settings(reload=True)
    tr._model_cache.clear()
    mock = MagicMock()
    with patch("core.transcribe.WhisperModel", return_value=mock):
        assert tr._get_model(cfg.whisper) is tr._get_model(cfg.whisper)

def test_cuda_unavailable():
    from core.gpu_profile import cuda_available

    import sys
    with patch.dict(sys.modules, {"torch": None}):
        assert cuda_available() is False

def test_fmt_ts():
    assert "," in tr._fmt_ts(65.5)
