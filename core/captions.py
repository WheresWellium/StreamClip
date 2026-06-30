"""
StreamClip — Caption Engine
Produces styled, animated, word-grouped captions burned directly into video.
Uses the ASS (Advanced SubStation Alpha) subtitle format for full animation
control: pop-in timing, outline, shadow, colour-coded gaming terms, emoji injection.

Styles available:
  gaming_impact  — Impact font, yellow/white, heavy outline, uppercase pop
  tiktok_pop     — Bold round font, per-word colour, scale-bounce animation
  minimal_white  — Clean white Helvetica, thin outline, lower thirds
  podcast_clean  — Neutral, word-by-word reveal, speaker-aware colouring
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import structlog

from core.config import Settings, CaptionConfig
from core.models import Transcript, Word

log = structlog.get_logger(__name__)


# ─── Gaming vocabulary: special emphasis words ────────────────────────────────

_GAMING_TERMS: set[str] = {
    "ACE", "CLUTCH", "ONE-TAP", "HEADSHOT", "NOSCOPE", "INSANE",
    "INSANE", "LET'S GO", "LETS GO", "LFG", "HOLY", "WHAT", "NO WAY",
    "DESTROYED", "ELIMINATED", "VICTORY", "ROYALE", "WINNER", "WINNER WINNER",
    "POG", "POGGERS", "GOATED", "GOAT", "W", "L", "GG", "GGWP",
    "RAGE", "RAGING", "CLIP", "CLIP IT", "CLIP THAT", "CHAT",
}

_NEGATIVE_TERMS: set[str] = {"FAIL", "DEAD", "ELIMINATED", "LOSS", "L", "RIP"}

# Emoji injection rules (keyword → emoji appended after the caption group)
_EMOJI_MAP: dict[str, str] = {
    "insane": "🤯", "clutch": "🎯", "rage": "😤", "let's go": "🔥",
    "holy": "😮", "gg": "👏", "goat": "🐐", "win": "🏆",
    "fail": "💀", "dead": "💀", "rip": "😂", "pog": "👀",
}


# ─── ASS style definitions ────────────────────────────────────────────────────

@dataclass
class _ASSStyle:
    name: str
    fontname: str
    fontsize: int
    primary_colour: str    # &HAABBGGRR in ASS format
    outline_colour: str
    shadow_colour: str
    bold: bool
    outline: float
    shadow: float
    alignment: int         # numpad alignment (2=bottom-centre, 8=top-centre)
    margin_v: int          # vertical margin in pixels


_STYLES: dict[str, _ASSStyle] = {
    "gaming_impact": _ASSStyle(
        name="GameImpact",
        fontname="Impact",
        fontsize=80,
        primary_colour="&H00FFFFFF",   # white
        outline_colour="&H00000000",   # black outline
        shadow_colour="&H80000000",    # semi-transparent black shadow
        bold=True,
        outline=5.0,
        shadow=3.0,
        alignment=2,                   # bottom centre
        margin_v=160,
    ),
    "tiktok_pop": _ASSStyle(
        name="TikTokPop",
        fontname="Arial Rounded MT Bold",
        fontsize=72,
        primary_colour="&H00FFFF00",   # yellow
        outline_colour="&H00000000",
        shadow_colour="&H60000000",
        bold=True,
        outline=4.0,
        shadow=2.0,
        alignment=2,
        margin_v=140,
    ),
    "minimal_white": _ASSStyle(
        name="Minimal",
        fontname="Helvetica Neue",
        fontsize=60,
        primary_colour="&H00FFFFFF",
        outline_colour="&H00000000",
        shadow_colour="&H40000000",
        bold=False,
        outline=2.5,
        shadow=1.5,
        alignment=2,
        margin_v=120,
    ),
    "podcast_clean": _ASSStyle(
        name="Podcast",
        fontname="SF Pro Display",
        fontsize=58,
        primary_colour="&H00FFFFFF",
        outline_colour="&H00333333",
        shadow_colour="&H30000000",
        bold=True,
        outline=2.0,
        shadow=1.0,
        alignment=2,
        margin_v=100,
    ),
}

# Per-emotion accent colours for highlighted words
_EMOTION_ACCENTS: dict[str, str] = {
    "hype":   "&H0000E5FF",   # neon yellow
    "rage":   "&H000000FF",   # red
    "funny":  "&H0000FF7F",   # lime
    "clutch": "&H0000BFFF",   # gold
    "fail":   "&H00FF4040",   # orange-red
    "weird":  "&H00FF00FF",   # magenta
    "neutral": "&H00FFFFFF",  # white
}


# ─── ASS file builder ─────────────────────────────────────────────────────────

class _ASSBuilder:
    def __init__(self, style: _ASSStyle) -> None:
        self.style = style
        self._events: list[str] = []

    def _header(self, video_w: int, video_h: int) -> str:
        s = self.style
        bold_int = -1 if s.bold else 0
        return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {s.name},{s.fontname},{s.fontsize},{s.primary_colour},&H00FFFFFF,{s.outline_colour},{s.shadow_colour},{bold_int},0,0,0,100,100,0,0,1,{s.outline},{s.shadow},{s.alignment},40,40,{s.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    @staticmethod
    def _ts(secs: float) -> str:
        """Format seconds as ASS timestamp: H:MM:SS.cc"""
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = secs % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    def add_line(
        self,
        start: float,
        end: float,
        text: str,
        emotion: str = "neutral",
        is_gaming_term: bool = False,
        emit_emoji: str = "",
    ) -> None:
        """Add a single caption line with optional pop-in animation."""
        accent = _EMOTION_ACCENTS.get(emotion, "&H00FFFFFF")

        # Pop-in scale animation: grow from 80% → 105% → 100% in 120ms
        pop_in = r"{\an5\t(0,60,\fscx80\fscy80)\t(60,120,\fscx105\fscy105)\t(120,180,\fscx100\fscy100)}"

        if is_gaming_term:
            # Colour flash: accent colour, then white
            styled_text = (
                f"{{\\c{accent}\\t(0,200,\\c{self.style.primary_colour})}}{text}{{\\r}}"
            )
        else:
            styled_text = text

        if emit_emoji:
            styled_text += f"  {emit_emoji}"

        # Reset positioning after animation override
        line_text = f"{pop_in}{styled_text}"
        self._events.append(
            f"Dialogue: 0,{self._ts(start)},{self._ts(end)},{self.style.name},,0,0,0,,{line_text}"
        )

    def render(self, video_w: int, video_h: int) -> str:
        return self._header(video_w, video_h) + "\n".join(self._events)


# ─── Word grouper ─────────────────────────────────────────────────────────────

class _WordGroup(NamedTuple):
    words: list[Word]
    text: str
    start: float
    end: float


def _group_words(
    words: list[Word],
    group_size: int,
    max_chars: int,
) -> list[_WordGroup]:
    """
    Chunk a flat word list into display groups.
    A new group is started when either group_size words are accumulated
    or a natural pause (>0.35s) is detected — whichever comes first.
    """
    groups: list[_WordGroup] = []
    buf: list[Word] = []

    for i, word in enumerate(words):
        buf.append(word)
        at_count = len(buf) >= group_size
        at_pause = (
            i + 1 < len(words)
            and words[i + 1].start - word.end > 0.35
        )
        at_max_chars = sum(len(w.text) for w in buf) > max_chars
        at_end = i == len(words) - 1

        if buf and (at_count or at_pause or at_max_chars or at_end):
            text = " ".join(w.text.upper() for w in buf).strip()
            groups.append(_WordGroup(
                words=list(buf),
                text=text,
                start=buf[0].start,
                end=buf[-1].end,
            ))
            buf = []

    return groups


def _detect_emoji(text: str) -> str:
    low = text.lower()
    for kw, emoji in _EMOJI_MAP.items():
        if kw in low:
            return emoji
    return ""


def _is_gaming_term(text: str) -> bool:
    return text.upper().strip(".,!?") in _GAMING_TERMS


# ─── Caption engine public API ─────────────────────────────────────────────────

def generate_captions(
    clip_path: Path,
    output_path: Path,
    transcript: Transcript,
    clip_start: float,
    clip_end: float,
    cfg: Settings,
    emotion: str = "neutral",
) -> Path:
    """
    Burn animated captions into a video clip.

    Args:
        clip_path:   The vertical 9:16 clip (post-reframe).
        output_path: Where to write the captioned output.
        transcript:  Full source transcript (segments will be filtered to clip window).
        clip_start:  Start time within the SOURCE video (used to filter segments).
        clip_end:    End time within the SOURCE video.
        cfg:         Global settings.
        emotion:     Clip emotion from LLM (controls accent colour).

    Returns:
        Path to the captioned output video.
    """
    ccfg: CaptionConfig = cfg.caption

    # ── Probe clip dimensions ─────────────────────────────────────────────
    import json as _json
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(clip_path)],
        capture_output=True, text=True, check=True,
    )
    streams = _json.loads(probe.stdout).get("streams", [])
    vstream = next((s for s in streams if s.get("codec_type") == "video"), {})
    video_w = int(vstream.get("width", cfg.reframe.target_width))
    video_h = int(vstream.get("height", cfg.reframe.target_height))

    # ── Collect words in the clip window ──────────────────────────────────
    all_words: list[Word] = []
    for seg in transcript.segments_in_range(clip_start, clip_end):
        for w in seg.words:
            if clip_start <= w.start <= clip_end:
                # Re-base timestamps relative to clip start
                all_words.append(Word(
                    text=w.text,
                    start=w.start - clip_start,
                    end=w.end - clip_start,
                    probability=w.probability,
                ))

    if not all_words:
        log.warning("no_words_in_clip_window", clip=str(clip_path))
        return clip_path  # no captions — return original

    # ── Group into display chunks ─────────────────────────────────────────
    groups = _group_words(all_words, ccfg.words_per_group, ccfg.max_chars_per_line)

    # ── Build ASS file ────────────────────────────────────────────────────
    style_def = _STYLES.get(ccfg.style, _STYLES["gaming_impact"])
    builder = _ASSBuilder(style_def)

    for group in groups:
        is_gaming = _is_gaming_term(group.text)
        emoji = _detect_emoji(group.text) if ccfg.add_emoji else ""
        builder.add_line(
            start=group.start,
            end=group.end + 0.05,   # tiny hold to prevent flicker
            text=group.text,
            emotion=emotion,
            is_gaming_term=is_gaming and ccfg.highlight_keywords,
            emit_emoji=emoji,
        )

    ass_content = builder.render(video_w, video_h)
    ass_path = clip_path.with_suffix(".ass")
    ass_path.write_text(ass_content, encoding="utf-8")

    # ── Burn into video via FFmpeg ────────────────────────────────────────
    # ASS filter: escaping backslashes and colons for Windows path compat
    ass_path_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
    ass_filter = f"ass={ass_path_escaped}"

    cmd = [
        "ffmpeg", "-y", "-i", str(clip_path),
        "-vf", ass_filter,
        "-c:v", "libx264", "-crf", "16", "-preset", "fast",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    log.debug("burning_captions", cmd=" ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)
    ass_path.unlink(missing_ok=True)  # clean up temp ASS file

    log.info("captions_done", output=str(output_path), num_groups=len(groups))
    return output_path
