"""Tests for peak-based window discovery."""

from __future__ import annotations

import numpy as np

from core.peak_detection import (
    dedupe_windows,
    find_peak_indices,
    merge_peak_times,
    smooth_series,
    windows_from_peaks,
)


def test_find_peak_indices_basic() -> None:
    values = np.array([0.1, 0.2, 0.9, 0.3, 0.85, 0.1])
    peaks = find_peak_indices(values, min_height=0.5, min_distance=2)
    assert 2 in peaks
    assert 4 in peaks


def test_merge_peak_times() -> None:
    merged = merge_peak_times([10.0, 12.0, 50.0, 55.0], merge_gap_secs=15.0)
    assert merged == [10.0, 50.0]


def test_windows_from_peaks_respects_duration() -> None:
    windows = windows_from_peaks(
        [30.0],
        padding_secs=5.0,
        min_duration=15.0,
        max_duration=90.0,
        source_duration=60.0,
    )
    assert len(windows) == 1
    start, end = windows[0]
    assert start >= 0
    assert end <= 60.0
    assert end - start >= 15.0


def test_dedupe_windows() -> None:
    windows = [(0.0, 30.0), (5.0, 35.0), (60.0, 90.0)]
    kept = dedupe_windows(windows, iou_threshold=0.3)
    assert len(kept) == 2


def test_smooth_series_preserves_length() -> None:
    arr = np.array([0.0, 1.0, 0.0, 1.0, 0.0])
    out = smooth_series(arr, 3)
    assert out.shape == arr.shape
