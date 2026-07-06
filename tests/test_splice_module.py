"""Unit tests for core/splice.py (ffmpeg concat + storage download)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import get_settings
from core.splice import download_clip_finals, splice_clip_files


@pytest.fixture
def cfg():
    return get_settings(reload=True)


def test_splice_requires_at_least_two_inputs(cfg, tmp_path):
    one = tmp_path / "a.mp4"
    one.write_bytes(b"v")
    with pytest.raises(ValueError, match="at least two"):
        splice_clip_files([one], tmp_path / "out.mp4", cfg)


def test_splice_concat_cut_uses_ffmpeg_concat(cfg, tmp_path):
    inputs = [tmp_path / f"c{i}.mp4" for i in range(3)]
    for p in inputs:
        p.write_bytes(b"vid")
    out = tmp_path / "merged.mp4"

    with patch("core.splice.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        result = splice_clip_files(inputs, out, cfg, transition="cut")

    assert result == out
    run.assert_called_once()
    cmd = run.call_args[0][0]
    assert "-f" in cmd and "concat" in cmd
    assert str(out) in cmd


def test_splice_crossfade_two_clips(cfg, tmp_path):
    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    out = tmp_path / "xfade.mp4"

    with patch("core.splice.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        splice_clip_files([a, b], out, cfg, transition="crossfade")

    cmd = run.call_args[0][0]
    assert "xfade" in " ".join(cmd)


def test_download_clip_finals(tmp_path):
    storage = MagicMock()

    def _download(key: str, dest: Path, on_progress=None) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(key.encode())

    storage.download.side_effect = _download
    paths = download_clip_finals(storage, ["clips/a.mp4", "clips/b.mp4"], tmp_path / "ws")
    assert len(paths) == 2
    assert paths[0].read_bytes() == b"clips/a.mp4"
    storage.download.assert_any_call("clips/a.mp4", paths[0])
