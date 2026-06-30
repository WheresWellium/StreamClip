"""
StreamClip — Twitch chat spike detection

Normalises chat message density into a 0–1 excitement score per time window.
Used during highlight discovery alongside audio and motion signals.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChatEvent:
    """Single chat line aligned to VOD playback time."""
    offset_secs: float
    text: str


class ChatSpikeAnalyser:
    """
    Builds a per-second message histogram and scores windows by spike intensity.

    Spike score = window message count vs the video's baseline rate (median
    messages/sec), capped at 1.0.
    """

    def __init__(self, events: list[ChatEvent], *, video_duration: float) -> None:
        self._duration = max(video_duration, 1.0)
        self._hist = self._build_histogram(events)

    @staticmethod
    def _build_histogram(events: list[ChatEvent]) -> np.ndarray:
        if not events:
            return np.zeros(1, dtype=np.float32)
        max_sec = int(max(e.offset_secs for e in events)) + 1
        hist = np.zeros(max(max_sec, 1), dtype=np.float32)
        for ev in events:
            idx = int(ev.offset_secs)
            if 0 <= idx < len(hist):
                hist[idx] += 1.0
        return hist

    def score(self, start: float, end: float) -> float:
        if self._hist.sum() == 0:
            return 0.0
        s = max(0, int(start))
        e = min(len(self._hist), int(np.ceil(end)))
        if e <= s:
            return 0.0
        window = self._hist[s:e]
        window_rate = float(window.sum()) / max(end - start, 0.5)
        baseline = float(np.median(self._hist)) if self._hist.size else 0.0
        baseline = max(baseline, 0.05)
        raw = window_rate / (baseline * 4.0)
        return float(min(1.0, raw))

    def per_second_curve(self, *, video_duration: float) -> np.ndarray:
        """Resample histogram to 1 Hz bins for peak detection."""
        n = max(int(np.ceil(video_duration)), 1)
        out = np.zeros(n, dtype=np.float32)
        limit = min(n, len(self._hist))
        if limit > 0:
            out[:limit] = self._hist[:limit]
        mx = float(out.max())
        return out / mx if mx > 0 else out
