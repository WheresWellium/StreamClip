"""
StreamClip — Highlight Detection Engine
Multi-signal ensemble that fuses:
  1. LLM virality scoring  (transcript-based, 0–100)
  2. Audio energy          (librosa RMS + onset strength)
  3. Spectral novelty      (spectral flux — sudden audio transitions)
  4. Optical flow          (OpenCV dense flow — visual excitement)
  5. Chat spike density    (Twitch chat message bursts, optional)

Each signal is normalised to [0, 1] independently before the
weighted ensemble is computed. Overlapping candidates are
deduplicated by a greedy IoU suppressor, then boundaries are
snapped to the nearest natural sentence break.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import structlog

from core.config import Settings, HighlightConfig, LLMConfig
from core.models import (
    ClipCandidate,
    Emotion,
    SignalScores,
    Transcript,
    TranscriptSegment,
)

log = structlog.get_logger(__name__)

# ─── LLM prompt ───────────────────────────────────────────────────────────────

_VIRALITY_PROMPT = """\
You are an expert gaming content strategist who has studied 100,000+ viral clips
across Twitch, TikTok, YouTube Shorts, and Instagram Reels.

Analyse this transcript segment from a gaming stream and score its clip potential.

── VIRAL SIGNALS (score high) ────────────────────────────────────────────────
• Kill streaks, clutch 1vX plays, last-second rounds won or lost
• Genuine emotional outbursts: rage, disbelief, pure joy, panic
• "This should have worked" fails and funny moments
• Quotable one-liners that land without context
• Unexpected plot twists in the gameplay narrative
• The moment everything changes — the exact frame someone wins or loses it

── ANTI-VIRAL SIGNALS (score low) ────────────────────────────────────────────
• Dead air, loading screens, menu navigation, setup chatter
• Repeated or filler content ("um", "uh", long pauses)
• Mid-explanation without visible payoff
• Spectator commentary with no gameplay action

── TRANSCRIPT ─────────────────────────────────────────────────────────────────
Segment {idx} | {start:.1f}s – {end:.1f}s | Duration: {duration:.1f}s

"{text}"

── OUTPUT FORMAT ──────────────────────────────────────────────────────────────
Return ONLY valid JSON (no markdown fences, no extra text):
{{
  "score": <integer 0–100>,
  "hook": "<TikTok-ready caption hook — 1 punchy sentence, present-tense verb>",
  "clip_title": "<4–6 word punchy title, title-case>",
  "emotion": "<one of: hype|rage|funny|clutch|fail|weird|neutral>",
  "meme_keywords": ["<keyword1>", "<keyword2>"],
  "reason": "<1–2 sentences explaining the score>"
}}"""


# ─── Signal 1: LLM Virality Scorer ────────────────────────────────────────────

class _LLMScorer:
    """Calls a local Ollama or remote LLM API to score transcript segments."""

    def __init__(self, cfg: LLMConfig) -> None:
        self.cfg = cfg
        self._client = self._build_client()

    def _build_client(self) -> Any:
        if self.cfg.provider == "ollama":
            from ollama import Client
            return Client(host=self.cfg.base_url)
        if self.cfg.provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=self.cfg.api_key, base_url=self.cfg.base_url)
        raise ValueError(f"Unknown LLM provider: {self.cfg.provider!r}")

    def _call(self, prompt: str) -> str:
        if self.cfg.provider == "ollama":
            resp = self._client.chat(
                model=self.cfg.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.cfg.temperature},
            )
            return resp.message.content.strip()
        # OpenAI-compatible
        resp = self._client.chat.completions.create(
            model=self.cfg.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.cfg.temperature,
            timeout=self.cfg.timeout_secs,
        )
        return resp.choices[0].message.content.strip()

    def score(self, seg: TranscriptSegment, idx: int) -> dict[str, Any]:
        prompt = _VIRALITY_PROMPT.format(
            idx=idx,
            start=seg.start,
            end=seg.end,
            duration=seg.duration,
            text=seg.text,
        )
        for attempt in range(self.cfg.max_retries):
            try:
                raw = self._call(prompt)
                # Strip any accidental markdown fences
                raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
                return json.loads(raw)
            except (json.JSONDecodeError, Exception) as exc:
                log.warning(
                    "llm_score_retry",
                    attempt=attempt + 1,
                    error=str(exc),
                    seg_id=seg.id,
                )
                time.sleep(1.5 ** attempt)
        # Fallback neutral score on total failure
        return {"score": 0, "hook": "", "clip_title": "", "emotion": "neutral",
                "meme_keywords": [], "reason": "LLM call failed"}


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
    if duration < min_dur:
        mid = (best_start + best_end) / 2
        best_start = max(0.0, mid - min_dur / 2)
        best_end = best_start + min_dur
    elif duration > max_dur:
        # Keep the end fixed, trim the tail
        best_end = min(best_end, best_start + max_dur)

    return best_start, best_end


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

class EnsembleScorer:
    """
    Combines all signal scorers into a single normalised rank score
    for each transcript segment.
    """

    def __init__(
        self,
        video_path: Path,
        cfg: Settings,
    ) -> None:
        self.hcfg: HighlightConfig = cfg.highlight
        self._llm = _LLMScorer(cfg.llm)
        self._audio = _AudioAnalyser(video_path)
        self._flow = _OpticalFlowAnalyser(video_path)

    def score_segment(
        self,
        seg: TranscriptSegment,
        idx: int,
    ) -> ClipCandidate | None:
        """Score a single segment across all signals. Returns None if below threshold."""
        h = self.hcfg

        # ── Signal 1: LLM ──────────────────────────────────────────────────
        llm_result = self._llm.score(seg, idx)
        llm_score_raw = float(llm_result.get("score", 0))

        if llm_score_raw < h.min_virality_score:
            log.debug(
                "segment_below_threshold",
                seg_id=seg.id,
                score=llm_score_raw,
                text=seg.text[:60],
            )
            return None

        # ── Signal 2: Audio energy ─────────────────────────────────────────
        audio_e = self._audio.energy(seg.start, seg.end)

        # ── Signal 3: Spectral novelty ─────────────────────────────────────
        spectral_n = self._audio.novelty(seg.start, seg.end)

        # ── Signal 4: Optical flow ─────────────────────────────────────────
        flow_s = self._flow.score(seg.start, seg.end)

        # ── Normalise LLM score to [0, 1] ─────────────────────────────────
        llm_norm = llm_score_raw / 100.0

        # ── Weighted ensemble ──────────────────────────────────────────────
        ensemble = (
            h.weight_llm_virality     * llm_norm
            + h.weight_audio_energy   * audio_e
            + h.weight_spectral_novelty * spectral_n
            + h.weight_optical_flow   * flow_s
            # chat_spikes is 0 unless a chat log is provided
        )

        scores = SignalScores(
            llm_virality=llm_score_raw,
            audio_energy=audio_e,
            spectral_novelty=spectral_n,
            optical_flow=flow_s,
        )
        scores.set_ensemble(ensemble)

        emotion_str = llm_result.get("emotion", "neutral")
        try:
            emotion = Emotion(emotion_str)
        except ValueError:
            emotion = Emotion.NEUTRAL

        return ClipCandidate(
            segment_id=seg.id,
            start=seg.start,
            end=seg.end,
            text=seg.text,
            scores=scores,
            llm_hook=llm_result.get("hook", ""),
            llm_title=llm_result.get("clip_title", ""),
            emotion=emotion,
            meme_keywords=llm_result.get("meme_keywords", []),
            llm_reason=llm_result.get("reason", ""),
        )


# ─── Main entry point ──────────────────────────────────────────────────────────

def find_highlights(
    transcript: Transcript,
    video_path: Path,
    cfg: Settings,
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
    log.info(
        "highlight_detection_start",
        num_segments=len(transcript.segments),
        target_clips=hcfg.target_clips,
    )

    scorer = EnsembleScorer(video_path=video_path, cfg=cfg)
    raw_candidates: list[ClipCandidate] = []

    for idx, seg in enumerate(transcript.segments):
        # Skip very short segments — not enough context
        if seg.duration < 5.0 or seg.word_count < 8:
            continue

        log.debug("scoring_segment", idx=idx, text=seg.text[:60])
        cand = scorer.score_segment(seg, idx)
        if cand is not None:
            raw_candidates.append(cand)

    log.info("raw_candidates", count=len(raw_candidates))

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
        )
        # Rebuild with snapped times (dataclass is frozen so rebuild it)
        snapped.append(
            ClipCandidate(
                segment_id=cand.segment_id,
                start=s,
                end=e,
                text=transcript.text_in_range(s, e),
                scores=cand.scores,
                llm_hook=cand.llm_hook,
                llm_title=cand.llm_title,
                emotion=cand.emotion,
                meme_keywords=cand.meme_keywords,
                llm_reason=cand.llm_reason,
            )
        )

    # ── Non-maximum suppression ────────────────────────────────────────────
    kept = _nms(snapped, iou_threshold=0.25)

    # ── Return top N ──────────────────────────────────────────────────────
    final = sorted(kept, key=lambda c: c.rank_score, reverse=True)[: hcfg.target_clips]

    log.info(
        "highlight_detection_done",
        candidates_after_nms=len(kept),
        returning=len(final),
        top_scores=[f"{c.rank_score:.3f}" for c in final],
    )
    return final
