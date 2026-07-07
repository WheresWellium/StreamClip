"""Phase 4 — audio-to-clip ingest tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.api.schemas import UploadInitRequest
from core.config import get_settings
from core.ingest.audio_slate import is_audio_only, render_audio_slate
from core.ingest.probe import probe_video
from core.models import VideoMeta


def _make_wav(path: Path, duration: float = 1.0) -> Path:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", "pcm_s16le", str(path),
        ],
        check=True, capture_output=True,
    )
    return path


def _meta(**overrides) -> VideoMeta:
    base = dict(
        path=Path("x"), url=None, title="t", duration=10.0,
        width=1920, height=1080, fps=30.0, size_bytes=100,
        has_audio=True, video_codec="h264", audio_codec="aac",
    )
    base.update(overrides)
    return VideoMeta(**base)


# ─── Upload MIME validation ───────────────────────────────────────────────────

def test_upload_init_accepts_video_and_audio_types():
    assert UploadInitRequest(filename="a.mp4", content_type="video/mp4").content_type == "video/mp4"
    assert UploadInitRequest(filename="a.mp3", content_type="audio/mpeg").content_type == "audio/mpeg"
    # Normalized to lowercase
    assert UploadInitRequest(filename="a.wav", content_type="Audio/WAV").content_type == "audio/wav"


def test_upload_init_rejects_unknown_types():
    with pytest.raises(ValidationError):
        UploadInitRequest(filename="a.pdf", content_type="application/pdf")
    with pytest.raises(ValidationError):
        UploadInitRequest(filename="a.gif", content_type="image/gif")


@pytest.mark.asyncio
async def test_upload_init_audio_gated_by_feature_flag(client):
    cfg = get_settings()
    old = cfg.features.audio_ingest
    try:
        cfg.features.audio_ingest = False
        resp = await client.post(
            "/api/uploads/init",
            json={"filename": "pod.mp3", "content_type": "audio/mpeg"},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "audio_ingest_disabled"

        cfg.features.audio_ingest = True
        resp = await client.post(
            "/api/uploads/init",
            json={"filename": "pod.mp3", "content_type": "audio/mpeg"},
        )
        assert resp.status_code == 201
        assert "storage_key" in resp.json()
    finally:
        cfg.features.audio_ingest = old


# ─── Audio detection ──────────────────────────────────────────────────────────

def test_is_audio_only_logic():
    assert is_audio_only(_meta(width=0, height=0, video_codec="none"))
    assert not is_audio_only(_meta())
    # Silent video is not audio-only
    assert not is_audio_only(_meta(has_audio=False))


def test_probe_detects_audio_only_wav(tmp_path: Path):
    wav = _make_wav(tmp_path / "tone.wav")
    meta = probe_video(wav)
    assert meta.has_audio
    assert meta.width == 0 and meta.height == 0
    assert is_audio_only(meta)
    assert meta.duration == pytest.approx(1.0, abs=0.2)


# ─── Slate rendering ──────────────────────────────────────────────────────────

def test_render_audio_slate_produces_vertical_video(tmp_path: Path):
    cfg = get_settings()
    wav = _make_wav(tmp_path / "tone.wav")
    out = tmp_path / "source.mp4"

    render_audio_slate(wav, out, cfg)

    assert out.exists() and out.stat().st_size > 0
    meta = probe_video(out)
    assert not is_audio_only(meta)
    assert meta.width == cfg.reframe.target_width
    assert meta.height == cfg.reframe.target_height
    assert meta.has_audio
    assert meta.duration == pytest.approx(1.0, abs=0.3)
