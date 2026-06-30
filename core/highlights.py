"""
StreamClip — Highlight Detection Engine
Multi-signal discovery that fuses:
  1. Audio energy          (librosa RMS + onset strength)
  2. Spectral novelty      (spectral flux — sudden audio transitions)
  3. Optical flow          (OpenCV dense flow — visual excitement)
  4. Chat spike density    (Twitch chat message bursts, optional)

LLM virality scoring runs post-hoc via ``core.virality`` after clips exist.
Each signal is normalised to [0, 1] before the weighted ensemble is computed.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import structlog

from core.config import Settings, HighlightConfig
from core.caption_timing import snap_time_to_words
from core.clip_metadata import derive_clip_metadata
from core.chat_spikes import ChatSpikeAnalyser
from core.content_profiles import ProfileWeights, get_profile
from core.peak_detection import (
    dedupe_windows,
    find_peak_indices,
    merge_peak_times,
    smooth_series,
    windows_from_peaks,
)
from core.models import (
    ClipCandidate,
    Emotion,
    SignalScores,
    Transcript,
    TranscriptSegment,
)

log = structlog.get_logger(__name__)

# ─── Signal 2 + 3: Audio Analyser ─────────────────────────────────────────────

class _AudioAnalyser:
    """
    Computes per-second audio energy and spectral novelty curves.
    Both are normalised to [0, 1] over the full video.
    """

    def __init__(self, video_path: Path) -> None:
        import librosa
        self._librosa = librosa
        log.info("loading_audio", path=str(video_path))
        self.y, self.sr = librosa.load(str(video_path), sr=22050, mono=True)
        self.duration = len(self.y) / self.sr

        # RMS energy — overall loudness
        hop = int(self.sr * 0.5)   # 0.5-second windows
        self._rms = librosa.feature.rms(y=self.y, hop_length=hop)[0]
        self._rms_times = librosa.times_like(self._rms, sr=self.sr, hop_length=hop)

        # Onset strength — sudden audio events
        self._onset = librosa.onset.onset_strength(y=self.y, sr=self.sr)
        self._onset_times = librosa.times_like(self._onset, sr=self.sr)

        # Normalise both to [0, 1]
        self._rms_norm = self._safe_norm(self._rms)
        self._onset_norm = self._safe_norm(self._onset)

    @staticmethod
    def _safe_norm(arr: np.ndarray) -> np.ndarray:
        mx = arr.max()
        return arr / mx if mx > 0 else arr

    def _window_mean(self, norm_arr: np.ndarray, times: np.ndarray,
                     start: float, end: float) -> float:
        mask = (times >= start) & (times <= end)
        if not mask.any():
            return 0.0
        # Use 90th-percentile rather than mean — captures peaks, not average
        return float(np.percentile(norm_arr[mask], 90))

    def energy(self, start: float, end: float) -> float:
        return self._window_mean(self._rms_norm, self._rms_times, start, end)

    def novelty(self, start: float, end: float) -> float:
        return self._window_mean(self._onset_norm, self._onset_times, start, end)

    def energy_curve(self) -> tuple[np.ndarray, np.ndarray]:
        """Per-sample times and normalised RMS energy (for peak detection)."""
        smoothed = self._rms_norm
        return self._rms_times.copy(), smoothed.copy()

    def onset_curve(self) -> tuple[np.ndarray, np.ndarray]:
        """Per-sample times and normalised onset strength."""
        return self._onset_times.copy(), self._onset_norm.copy()


# ─── Signal 4: Optical Flow Analyser ─────────────────────────────────────────

class _OpticalFlowAnalyser:
    """
    Samples N frames per second from the video and computes
    dense Farneback optical flow magnitude as a visual excitement proxy.
    """

    def __init__(self, video_path: Path, sample_fps: float = 2.0) -> None:
        self.path = video_path
        self.sample_fps = sample_fps
        self._curve: list[tuple[float, float]] = []  # (time, score)
        self._computed = False

    def _ensure_computed(self) -> None:
        if self._computed:
            return
        log.info("computing_optical_flow", path=str(self.path))
        cap = cv2.VideoCapture(str(self.path))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        step = max(1, int(src_fps / self.sample_fps))

        prev_gray: np.ndarray | None = None
        frame_idx = 0
        scores: list[tuple[float, float]] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            t = frame_idx / src_fps
            frame_idx += 1

            if frame_idx % step != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 180))   # downscale for speed

            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
                )
                magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
                scores.append((t, float(np.mean(magnitude))))

            prev_gray = gray

        cap.release()

        if scores:
            values = np.array([s[1] for s in scores])
            mx = values.max()
            if mx > 0:
                values /= mx
            self._curve = [(t, float(v)) for (t, _), v in zip(scores, values)]
        self._computed = True

    def score(self, start: float, end: float) -> float:
        self._ensure_computed()
        window = [v for t, v in self._curve if start <= t <= end]
        if not window:
            return 0.0
        return float(np.percentile(window, 90))


# ─── Clip boundary optimiser ──────────────────────────────────────────────────

def _snap_boundaries(
    start: float,
    end: float,
    transcript: Transcript,
    padding: float = 2.5,
    min_dur: float = 15.0,
    max_dur: float = 90.0,
    *,
    source_duration: float | None = None,
) -> tuple[float, float]:
    """
    Snap a clip's start/end to the nearest sentence boundary
    so clips never begin or end mid-word.
    """
    all_segs = transcript.segments

    # Walk backward from `start` to find the start of a sentence
    best_start = max(0.0, start - padding)
    for seg in reversed(all_segs):
        if seg.start <= start:
            best_start = max(0.0, seg.start - 0.25)
            break

    # Walk forward from `end` to find the end of a sentence
    best_end = end + padding
    for seg in all_segs:
        if seg.end >= end:
            best_end = seg.end + 0.25
            break

    # Enforce duration constraints
    duration = best_end - best_start
    if source_duration is not None and source_duration <= min_dur:
        return 0.0, source_duration

    if duration < min_dur:
        mid = (best_start + best_end) / 2
        best_start = max(0.0, mid - min_dur / 2)
        best_end = best_start + min_dur
    elif duration > max_dur:
        best_end = min(best_end, best_start + max_dur)

    return snap_time_to_words(best_start, best_end, transcript)


# ─── Non-maximum suppression ──────────────────────────────────────────────────

def _iou(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union > 0 else 0.0


def _nms(candidates: list[ClipCandidate], iou_threshold: float = 0.3) -> list[ClipCandidate]:
    """
    Greedy NMS: sort by score descending, keep a candidate only if it
    does not overlap more than iou_threshold with any already-kept candidate.
    """
    sorted_cands = sorted(candidates, key=lambda c: c.rank_score, reverse=True)
    kept: list[ClipCandidate] = []
    for cand in sorted_cands:
        overlap = any(
            _iou(cand.start, cand.end, k.start, k.end) > iou_threshold
            for k in kept
        )
        if not overlap:
            kept.append(cand)
    return kept


# ─── Ensemble Scorer ──────────────────────────────────────────────────────────

class _NullFlowAnalyser:
    """No-op stand-in when optical flow is skipped for short-tier ingest."""

    def score(self, start: float, end: float) -> float:
        return 0.0


class EnsembleScorer:
    """
    Discovery scorer — audio, spectral novelty, optical flow, and chat spikes.

    LLM virality runs later via ``core.virality.score_clip_virality``.
    """

    def __init__(
        self,
        video_path: Path,
        cfg: Settings,
        *,
        skip_optical_flow: bool = False,
        chat_analyser: ChatSpikeAnalyser | None = None,
        profile: ProfileWeights | None = None,
    ) -> None:
        self.hcfg: HighlightConfig = cfg.highlight
        self._profile = profile
        self._skip_flow = skip_optical_flow
        self._chat = chat_analyser
        self._audio = _AudioAnalyser(video_path)
        self._flow: _NullFlowAnalyser | _OpticalFlowAnalyser
        if skip_optical_flow:
            self._flow = _NullFlowAnalyser()
            log.info("optical_flow_skipped", reason="processing_tier_hint")
        else:
            self._flow = _OpticalFlowAnalyser(video_path)

    def _weights(self) -> tuple[float, float, float, float]:
        if self._profile:
            return (
                self._profile.weight_audio_energy,
                self._profile.weight_spectral_novelty,
                0.0 if self._skip_flow else self._profile.weight_optical_flow,
                self._profile.weight_chat_spikes if self._chat else 0.0,
            )
        h = self.hcfg
        w_flow = 0.0 if self._skip_flow else h.weight_optical_flow
        w_chat = h.weight_chat_spikes if self._chat else 0.0
        return h.weight_audio_energy, h.weight_spectral_novelty, w_flow, w_chat

    def score_segment(
        self,
        seg: TranscriptSegment,
        idx: int,
    ) -> ClipCandidate:
        """Score a segment for discovery (no LLM)."""
        w_audio, w_spectral, w_flow, w_chat = self._weights()
        w_total = w_audio + w_spectral + w_flow + w_chat
        if w_total <= 0:
            w_total = 1.0

        audio_e = self._audio.energy(seg.start, seg.end)
        spectral_n = self._audio.novelty(seg.start, seg.end)
        flow_s = self._flow.score(seg.start, seg.end)
        chat_s = self._chat.score(seg.start, seg.end) if self._chat else 0.0

        discovery = (
            w_audio * audio_e
            + w_spectral * spectral_n
            + w_flow * flow_s
            + w_chat * chat_s
        ) / w_total

        scores = SignalScores(
            llm_virality=0.0,
            audio_energy=audio_e,
            spectral_novelty=spectral_n,
            optical_flow=flow_s,
            chat_spikes=chat_s,
        )
        scores.set_ensemble(discovery)

        return ClipCandidate(
            segment_id=seg.id,
            start=seg.start,
            end=seg.end,
            text=seg.text,
            scores=scores,
            llm_hook="",
            llm_title="",
            emotion=Emotion.NEUTRAL,
            meme_keywords=[],
            llm_reason="",
        )


def _guaranteed_clips(
    transcript: Transcript,
    hcfg: HighlightConfig,
) -> list[ClipCandidate]:
    """
    Always produce at least one clip when scoring filters everything out.

    Splits the source into up to ``target_clips`` contiguous chunks so short
    or quiet videos still render.
    """
    duration = transcript.duration
    if duration <= 0:
        return []

    target = hcfg.target_clips
    min_dur = min(hcfg.min_clip_duration, duration)
    max_dur = min(hcfg.max_clip_duration, duration)

    # Short sources (Twitch clips, etc.) → one clip spanning the full video
    if duration <= 120:
        n = 1
    else:
        n = min(target, max(1, int(duration // min_dur))) if min_dur > 0 else 1
        if duration < hcfg.min_clip_duration:
            n = 1

    chunk_len = min(max_dur, duration / n)
    chunk_len = max(chunk_len, min_dur) if n == 1 else chunk_len

    candidates: list[ClipCandidate] = []
    start = 0.0
    for i in range(n):
        end = duration if i == n - 1 else min(duration, start + chunk_len)
        if end - start < 1.0:
            break

        text = transcript.text_in_range(start, end)
        title, hook = derive_clip_metadata(text)
        scores = SignalScores()
        scores.set_ensemble(0.0)

        candidates.append(
            ClipCandidate(
                segment_id=-(i + 1),
                start=start,
                end=end,
                text=text,
                scores=scores,
                llm_hook=hook,
                llm_title=title,
                emotion=Emotion.NEUTRAL,
                meme_keywords=[],
                llm_reason=(
                    "Guaranteed clip — source did not yield scored segments "
                    "but was exported anyway."
                ),
            )
        )
        start = end
        if start >= duration - 0.5:
            break

    log.info("highlight_guaranteed_clips", count=len(candidates), duration_secs=duration)
    return candidates


def _score_window(
    scorer: EnsembleScorer,
    start: float,
    end: float,
    transcript: Transcript,
    *,
    segment_id: int,
) -> ClipCandidate:
    """Score an arbitrary time window (peak-based or hybrid discovery)."""
    from core.models import TranscriptSegment

    text = transcript.text_in_range(start, end)
    pseudo = TranscriptSegment(
        id=segment_id,
        start=start,
        end=end,
        text=text,
        words=(),
    )
    cand = scorer.score_segment(pseudo, segment_id)
    title, hook = derive_clip_metadata(text)
    cand.llm_title = title
    cand.llm_hook = hook
    cand.text = text
    return cand


def _discover_peak_windows(
    scorer: EnsembleScorer,
    chat_analyser: ChatSpikeAnalyser | None,
    *,
    duration: float,
    hcfg: HighlightConfig,
    profile: ProfileWeights,
) -> list[tuple[float, float]]:
    """Find candidate windows from smoothed audio + chat peak curves."""
    win = max(1, hcfg.score_smoothing_window_secs * 2)
    min_height = profile.peak_min_height
    merge_gap = profile.peak_merge_gap_secs

    times, energy = scorer._audio.energy_curve()  # noqa: SLF001
    if energy.size > 0:
        energy = smooth_series(energy, win)
        audio_peaks = [float(times[i]) for i in find_peak_indices(energy, min_height=min_height)]
    else:
        audio_peaks = []

    chat_peaks: list[float] = []
    if chat_analyser is not None:
        chat_curve = chat_analyser.per_second_curve(video_duration=duration)
        chat_smooth = smooth_series(chat_curve, win)
        chat_peaks = [
            float(i) for i in find_peak_indices(chat_smooth, min_height=min_height * 0.85)
        ]

    merged = merge_peak_times(audio_peaks + chat_peaks, merge_gap_secs=merge_gap)
    windows = windows_from_peaks(
        merged,
        padding_secs=hcfg.clip_padding_secs * 3,
        min_duration=hcfg.min_clip_duration,
        max_duration=hcfg.max_clip_duration,
        source_duration=duration,
    )
    return dedupe_windows(windows)


# ─── Main entry point ──────────────────────────────────────────────────────────

def find_highlights(
    transcript: Transcript,
    video_path: Path,
    cfg: Settings,
    *,
    pipeline_hints: dict | None = None,
    source_url: str | None = None,
    chat_cache_path: Path | None = None,
) -> list[ClipCandidate]:
    """
    Run the full multi-signal highlight pipeline and return the top N
    non-overlapping, boundary-snapped clip candidates.

    Args:
        transcript:   Whisper transcript from transcribe.transcribe().
        video_path:   Path to the source video (for audio + optical flow).
        cfg:          Global settings.

    Returns:
        Sorted list of ClipCandidate (best first).
    """
    hcfg = cfg.highlight
    hints = pipeline_hints or {}
    skip_flow = bool(hints.get("skip_optical_flow", False))
    min_seg_dur = float(hints.get("min_clip_duration_override", 5.0))
    content_profile = hints.get("content_profile", "gaming")
    profile = get_profile(str(content_profile))
    candidate_mode = hcfg.candidate_mode

    log.info(
        "highlight_detection_start",
        num_segments=len(transcript.segments),
        target_clips=hcfg.target_clips,
        skip_optical_flow=skip_flow,
        candidate_mode=candidate_mode,
        content_profile=content_profile,
    )

    chat_analyser: ChatSpikeAnalyser | None = None
    if source_url or chat_cache_path:
        from core.twitch_chat import fetch_vod_chat

        chat_events = fetch_vod_chat(
            source_url=source_url,
            cfg=cfg,
            cache_path=chat_cache_path,
        )
        if chat_events:
            chat_analyser = ChatSpikeAnalyser(
                chat_events, video_duration=transcript.duration,
            )
            log.info("chat_spike_analyser_ready", events=len(chat_events))

    scorer = EnsembleScorer(
        video_path=video_path,
        cfg=cfg,
        skip_optical_flow=skip_flow,
        chat_analyser=chat_analyser,
        profile=profile,
    )
    raw_candidates: list[ClipCandidate] = []
    segments = transcript.segments

    is_short_source = transcript.duration <= 120
    min_words = 3 if is_short_source else 8
    effective_min_seg = min(min_seg_dur, max(2.0, transcript.duration / 6))

    use_segments = candidate_mode in ("segments", "hybrid")
    use_peaks = candidate_mode in ("peaks", "hybrid") and not is_short_source

    if use_segments:
        for idx, seg in enumerate(segments):
            spoken_words = max(seg.word_count, len(seg.text.split()))
            if len(segments) > 1:
                if seg.duration < effective_min_seg or spoken_words < min_words:
                    continue
            log.debug("scoring_segment", idx=idx, text=seg.text[:60])
            raw_candidates.append(scorer.score_segment(seg, idx))

    if use_peaks:
        peak_windows = _discover_peak_windows(
            scorer,
            chat_analyser,
            duration=transcript.duration,
            hcfg=hcfg,
            profile=profile,
        )
        log.info("peak_windows", count=len(peak_windows))
        base_id = len(raw_candidates)
        for i, (start, end) in enumerate(peak_windows):
            raw_candidates.append(
                _score_window(
                    scorer, start, end, transcript, segment_id=base_id + i,
                ),
            )

    log.info("raw_candidates", count=len(raw_candidates))

    max_pool = hcfg.target_clips * 6
    if len(raw_candidates) > max_pool:
        raw_candidates = sorted(
            raw_candidates, key=lambda c: c.rank_score, reverse=True,
        )[:max_pool]
        log.info("raw_candidates_capped", kept=len(raw_candidates), max_pool=max_pool)

    if not raw_candidates:
        log.info("highlight_fallback", reason="no_scored_segments")
        return _guaranteed_clips(transcript, hcfg)[: hcfg.target_clips]

    # ── Snap boundaries to sentence breaks ────────────────────────────────
    snapped: list[ClipCandidate] = []
    for cand in raw_candidates:
        s, e = _snap_boundaries(
            cand.start,
            cand.end,
            transcript,
            padding=hcfg.clip_padding_secs,
            min_dur=hcfg.min_clip_duration,
            max_dur=hcfg.max_clip_duration,
            source_duration=transcript.duration,
        )
        # Rebuild with snapped times; title/hook come from the actual clip transcript
        clip_text = transcript.text_in_range(s, e)
        title, hook = derive_clip_metadata(clip_text)
        snapped.append(
            ClipCandidate(
                segment_id=cand.segment_id,
                start=s,
                end=e,
                text=clip_text,
                scores=cand.scores,
                llm_hook=hook,
                llm_title=title,
                emotion=cand.emotion,
                meme_keywords=cand.meme_keywords,
                llm_reason=cand.llm_reason,
            )
        )

    # ── Non-maximum suppression ────────────────────────────────────────────
    kept = _nms(snapped, iou_threshold=0.25)

    # ── Return top N ──────────────────────────────────────────────────────
    final = sorted(kept, key=lambda c: c.rank_score, reverse=True)[: hcfg.target_clips]

    if not final:
        log.info("highlight_fallback", reason="nms_or_snap_removed_all")
        final = _guaranteed_clips(transcript, hcfg)[: hcfg.target_clips]

    log.info(
        "highlight_detection_done",
        candidates_after_nms=len(kept),
        returning=len(final),
        top_scores=[f"{c.rank_score:.3f}" for c in final],
    )
    return final
