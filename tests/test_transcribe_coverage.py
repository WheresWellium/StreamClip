"""Transcribe module coverage with mocked Whisper (no GPU / model download)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core import transcribe as tr
from core.config import get_settings
from core.models import Transcript, TranscriptSegment, Word


def _sample_transcript(path: Path) -> Transcript:
    w = Word(text="hi", start=0.0, end=0.5, probability=0.9)
    seg = TranscriptSegment(id=0, text="hi", start=0.0, end=1.0, words=(w,))
    return Transcript(segments=[seg], language="en", duration=1.0, source_path=path)


def test_video_hash_small_and_large(tmp_path):
    small = tmp_path / "small.bin"
    small.write_bytes(b"abc")
    assert len(tr._video_hash(small)) == 20

    large = tmp_path / "big.bin"
    large.write_bytes(b"a" * (3 * 1024 * 1024))
    assert len(tr._video_hash(large)) == 20
    assert tr._video_hash(small) != tr._video_hash(large)


def test_cache_roundtrip(tmp_path):
    t = _sample_transcript(tmp_path / "v.mp4")
    cp = tmp_path / "nested" / "c.json"
    tr._save_transcript(t, cp)
    assert tr._load_transcript(cp).segments[0].text == "hi"
    assert tr.save_transcript_json(t, cp) == cp


def test_transcribe_cache_hit_skips_model(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"x")
    cp = tr._cache_path(vid, tmp_path, cfg.whisper.model_size)
    tr._save_transcript(_sample_transcript(vid), cp)
    with patch.object(tr, "_get_model") as get_model:
        out = tr.transcribe(vid, cfg)
    assert out.duration == 1.0
    get_model.assert_not_called()


def test_transcribe_force_bypasses_cache(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"x")
    cp = tr._cache_path(vid, tmp_path, cfg.whisper.model_size)
    tr._save_transcript(_sample_transcript(vid), cp)

    seg = TranscriptSegment(id=0, text="forced", start=0.0, end=1.0, words=())
    info = MagicMock(language="en", duration=3.0)
    model = MagicMock()
    model.transcribe.return_value = (iter([]), info)
    with patch.object(tr, "_get_model", return_value=model), patch.object(
        tr, "_parse_segments", return_value=[seg]
    ):
        out = tr.transcribe(vid, cfg, force=True)
    assert out.duration == 3.0
    assert out.segments[0].text == "forced"
    model.transcribe.assert_called_once()


def test_transcribe_and_clip_mock_model_kwargs(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    vid = tmp_path / "v2.mp4"
    vid.write_bytes(b"y")
    seg = TranscriptSegment(id=0, text="a", start=0.0, end=1.0, words=())
    info = MagicMock(language="en", duration=2.0)
    model = MagicMock()
    model.transcribe.return_value = (iter([]), info)
    with patch.object(tr, "_get_model", return_value=model), patch.object(
        tr, "_parse_segments", return_value=[seg]
    ):
        out = tr.transcribe(vid, cfg, force=True)
        clip_out = tr.transcribe_clip(vid, cfg)

    assert out.duration == 2.0
    assert clip_out.language == "en"

    full_kwargs = model.transcribe.call_args_list[0].kwargs
    assert "clutch" in full_kwargs["hotwords"]
    assert full_kwargs["condition_on_previous_text"] is True
    assert full_kwargs["vad_filter"] == cfg.whisper.vad_filter

    clip_kwargs = model.transcribe.call_args_list[1].kwargs
    assert clip_kwargs["vad_filter"] == cfg.whisper.clip_vad_filter
    assert clip_kwargs["condition_on_previous_text"] is False
    assert clip_kwargs["word_timestamps"] is True


def test_load_job_transcript_local(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    job_ws = tmp_path / "jobs" / "job1"
    job_ws.mkdir(parents=True)
    local = job_ws / "transcript.json"
    tr._save_transcript(_sample_transcript(tmp_path / "v.mp4"), local)
    assert tr.load_job_transcript("job1", cfg).segments


def test_load_job_transcript_explicit_source(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "workspace_dir", tmp_path)
    src = tmp_path / "explicit.mp4"
    src.write_bytes(b"vid")
    storage = MagicMock()
    storage.exists.return_value = False
    sample = _sample_transcript(src)
    with patch.object(tr, "transcribe", return_value=sample) as mock_tr:
        out = tr.load_job_transcript(
            "job-explicit",
            cfg,
            storage=storage,
            source_path=src,
        )
    assert out.segments[0].text == "hi"
    mock_tr.assert_called_once_with(src, cfg)


def test_get_model_cached():
    cfg = get_settings(reload=True)
    tr._model_cache.clear()
    mock = MagicMock()
    with patch("core.transcribe.WhisperModel", return_value=mock):
        assert tr._get_model(cfg.whisper) is tr._get_model(cfg.whisper)


def test_cuda_unavailable():
    """GPU probe must fail closed when torch is absent (sidecar / CI)."""
    import sys

    from core.gpu_profile import cuda_available

    with patch.dict(sys.modules, {"torch": None}):
        assert cuda_available() is False
