"""
Peak-based highlight window discovery.

Inspired by research (Ringer et al. 2018; UPC LoL multimodal) and OSS patterns
(live-clip-finder, twitch-clip-miner): excitement moments cluster around
audio and chat spikes rather than arbitrary transcript segment boundaries.
"""

from __future__ import annotations

import numpy as np
import structlog

log = structlog.get_logger(__name__)


def smooth_series(values: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average; window >= 1."""
    if window <= 1 or values.size == 0:
        return values.astype(np.float64, copy=False)
    kernel = np.ones(window, dtype=np.float64) / window
    padded = np.pad(values.astype(np.float64), (window // 2, window - 1 - window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def find_peak_indices(
    values: np.ndarray,
    *,
    min_height: float = 0.55,
    min_distance: int = 3,
) -> list[int]:
    """
    Return indices of local maxima above ``min_height`` separated by ``min_distance``.
    """
    if values.size == 0:
        return []
    peaks: list[int] = []
    for i in range(1, len(values) - 1):
        if values[i] < min_height:
            continue
        if values[i] >= values[i - 1] and values[i] > values[i + 1]:
            if peaks and (i - peaks[-1]) < min_distance:
                if values[i] > values[peaks[-1]]:
                    peaks[-1] = i
            else:
                peaks.append(i)
    if values.size >= 2 and values[-1] >= min_height and values[-1] >= values[-2]:
        if not peaks or (len(values) - 1 - peaks[-1]) >= min_distance:
            peaks.append(len(values) - 1)
    return peaks


def merge_peak_times(
    peak_secs: list[float],
    *,
    merge_gap_secs: float,
) -> list[float]:
    """Merge peaks within ``merge_gap_secs``, keeping the earliest in each cluster."""
    if not peak_secs:
        return []
    ordered = sorted(peak_secs)
    merged: list[float] = [ordered[0]]
    for t in ordered[1:]:
        if t - merged[-1] <= merge_gap_secs:
            continue
        merged.append(t)
    return merged


def windows_from_peaks(
    peak_secs: list[float],
    *,
    padding_secs: float,
    min_duration: float,
    max_duration: float,
    source_duration: float,
) -> list[tuple[float, float]]:
    """Convert peak timestamps into clip candidate windows."""
    windows: list[tuple[float, float]] = []
    for peak in peak_secs:
        start = max(0.0, peak - padding_secs)
        end = min(source_duration, peak + padding_secs)
        duration = end - start
        if duration < min_duration:
            mid = (start + end) / 2
            start = max(0.0, mid - min_duration / 2)
            end = min(source_duration, start + min_duration)
        if duration > max_duration:
            end = start + max_duration
        if end - start >= 1.0:
            windows.append((start, end))
    return windows


def dedupe_windows(
    windows: list[tuple[float, float]],
    *,
    iou_threshold: float = 0.35,
) -> list[tuple[float, float]]:
    """Greedy deduplication of overlapping windows."""
    if not windows:
        return []

    def iou(a: tuple[float, float], b: tuple[float, float]) -> float:
        inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
        union = (a[1] - a[0]) + (b[1] - b[0]) - inter
        return inter / union if union > 0 else 0.0

    sorted_w = sorted(windows, key=lambda w: w[1] - w[0], reverse=True)
    kept: list[tuple[float, float]] = []
    for w in sorted_w:
        if any(iou(w, k) > iou_threshold for k in kept):
            continue
        kept.append(w)
    return kept
