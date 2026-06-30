"""Tests for FFmpeg helper utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.ffmpeg_utils import probe_duration, validate_output_duration


@patch("core.ffmpeg_utils.subprocess.run")
def test_probe_duration_parses_json(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        stdout='{"format": {"duration": "42.5"}}',
        returncode=0,
    )
    assert probe_duration(Path("fake.mp4")) == 42.5


@patch("core.ffmpeg_utils.probe_duration", return_value=30.0)
def test_validate_output_duration_within_tolerance(mock_probe: MagicMock) -> None:
    assert validate_output_duration(Path("out.mp4"), 29.5, tolerance_secs=1.5) is True


@patch("core.ffmpeg_utils.probe_duration", return_value=20.0)
def test_validate_output_duration_mismatch(mock_probe: MagicMock) -> None:
    assert validate_output_duration(Path("out.mp4"), 30.0, tolerance_secs=1.0) is False
