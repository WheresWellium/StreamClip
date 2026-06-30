"""
StreamClip — Core Data Models
Immutable dataclasses shared across every pipeline stage.
All timestamps are in seconds (float) relative to the source video start.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ─── Enums ────────────────────────────────────────────────────────────────────

class Emotion(str, Enum):
    HYPE      = "hype"
    RAGE      = "rage"
    FUNNY     = "funny"
    CLUTCH    = "clutch"
    FAIL      = "fail"
    WEIRD     = "weird"
    NEUTRAL   = "neutral"


class ClipStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    ERROR      = "error"


# ─── Transcript structures ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    probability: float          # Whisper confidence [0, 1]

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class TranscriptSegment:
    id: int
    text: str
    start: float
    end: float
    words: tuple[Word, ...]     # word-level timestamps from WhisperX
    speaker: str | None = None  # from diarisation, e.g. "SPEAKER_00"

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def words_per_second(self) -> float:
        return self.word_count / max(self.duration, 0.001)


@dataclass
class Transcript:
    segments: list[TranscriptSegment]
    language: str
    duration: float             # total source video duration
    source_path: Path

    def segments_in_range(self, start: float, end: float) -> list[TranscriptSegment]:
        return [s for s in self.segments if s.start < end and s.end > start]

    def text_in_range(self, start: float, end: float) -> str:
        segs = self.segments_in_range(start, end)
        return " ".join(s.text for s in segs)


# ─── Scoring structures ────────────────────────────────────────────────────────

@dataclass
class SignalScores:
    """Raw (un-normalised) scores from each detection signal."""
    llm_virality: float = 0.0       # 0–100 from the LLM
    audio_energy: float = 0.0       # 0–1 RMS + onset strength
    spectral_novelty: float = 0.0   # 0–1 spectral flux
    optical_flow: float = 0.0       # 0–1 mean optical-flow magnitude
    chat_spikes: float = 0.0        # 0–1 normalised chat-message density

    @property
    def ensemble(self) -> float:
        """Weighted sum; weights injected after normalisation by EnsembleScorer."""
        return self._ensemble_cache if hasattr(self, "_ensemble_cache") else 0.0

    def set_ensemble(self, value: float) -> None:
        object.__setattr__(self, "_ensemble_cache", value)


# ─── Clip structures ───────────────────────────────────────────────────────────

@dataclass
class ClipCandidate:
    """A ranked highlight candidate before any video processing."""
    segment_id: int
    start: float
    end: float
    text: str                       # transcript text in window
    scores: SignalScores
    llm_hook: str = ""              # TikTok-style caption hook
    llm_title: str = ""             # 4–6 word punchy title
    emotion: Emotion = Emotion.NEUTRAL
    meme_keywords: list[str] = field(default_factory=list)
    llm_reason: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def rank_score(self) -> float:
        return self.scores.ensemble


@dataclass
class OverlayAsset:
    """A meme/GIF/sticker asset matched to a clip moment."""
    asset_path: Path
    asset_type: str                 # "gif" | "png" | "mp4"
    sfx_path: Path | None
    trigger_time: float             # seconds into the clip
    duration: float                 # how long to show it
    position: str                   # "top_right" | "bottom_left" | …
    similarity_score: float         # cosine similarity that matched it
    matched_keyword: str


@dataclass
class ProcessedClip:
    """A fully rendered clip, ready to publish."""
    candidate: ClipCandidate
    source_path: Path               # original source video
    raw_clip_path: Path             # extracted 16:9 clip
    vertical_path: Path             # 9:16 reframed clip
    captioned_path: Path            # captions burned in
    final_path: Path                # overlays composited → final output
    overlays: list[OverlayAsset]
    render_time_secs: float
    status: ClipStatus = ClipStatus.DONE
    error: str | None = None

    @property
    def filename(self) -> str:
        return self.final_path.name


# ─── Job structures ────────────────────────────────────────────────────────────

@dataclass
class VideoMeta:
    """Metadata extracted from source before any processing."""
    path: Path
    url: str | None
    title: str
    duration: float
    width: int
    height: int
    fps: float
    size_bytes: int
    has_audio: bool
    video_codec: str
    audio_codec: str

    @property
    def aspect_ratio(self) -> float:
        return self.width / max(self.height, 1)

    @property
    def is_vertical(self) -> bool:
        return self.aspect_ratio < 1.0


@dataclass
class PipelineJob:
    """Top-level job tracking object passed through the entire pipeline."""
    job_id: str
    source_url: str | None
    source_path: Path | None
    meta: VideoMeta | None = None
    transcript: Transcript | None = None
    candidates: list[ClipCandidate] = field(default_factory=list)
    clips: list[ProcessedClip] = field(default_factory=list)
    status: ClipStatus = ClipStatus.PENDING
    progress: float = 0.0           # 0.0 – 1.0
    stage: str = "initialising"
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
