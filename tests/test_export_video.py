"""Export video ffmpeg args tests."""

from __future__ import annotations

from core.config import ExportConfig
from core.export_video import audio_encode_args, output_fps_args, video_encode_args


def test_libx264_encode_args():
    cfg = ExportConfig(codec="libx264", crf=17, preset="fast", fps=60)
    args = video_encode_args(cfg)
    assert "-c:v" in args and "libx264" in args
    assert "-crf" in args and "17" in args


def test_nvenc_encode_args():
    cfg = ExportConfig(codec="h264_nvenc", crf=17, preset="fast", fps=60)
    args = video_encode_args(cfg)
    assert "h264_nvenc" in args
    assert "-cq" in args


def test_output_fps_minimum_sixty():
    cfg = ExportConfig(fps=60)
    assert output_fps_args(cfg) == ["-r", "60"]
