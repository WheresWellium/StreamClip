"""
Caption export helpers — SRT, VTT, and TTML for job/clip transcripts.

Kept separate from core.transcribe so API export paths do not import faster-whisper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape

from core.caption_timing import collect_words_for_window, finalize_display_groups, group_words_for_display
from core.models import Transcript, TranscriptSegment, Word

CaptionExportFormat = Literal["srt", "vtt", "ttml", "ass"]


def _fmt_ts(secs: float, separator: str = ".") -> str:
    """Format seconds as HH:MM:SS.mmm (VTT/TTML) or HH:MM:SS,mmm (SRT)."""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int((secs % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{separator}{ms:03d}"


def build_export_transcript(
    transcript: Transcript,
    *,
    window_start: float | None = None,
    window_end: float | None = None,
    word_level: bool = True,
    words_per_group: int = 3,
    max_chars_per_line: int = 25,
    min_probability: float = 0.25,
) -> Transcript:
    """
    Build a transcript view suitable for subtitle export.

    When ``word_level`` is true, words are grouped with the same heuristics as
    the burn-in caption renderer (``group_words_for_display``).
    """
    start = window_start if window_start is not None else 0.0
    end = window_end if window_end is not None else transcript.duration

    if word_level:
        words = collect_words_for_window(
            transcript,
            start,
            end,
            rebase_to=start,
            min_probability=min_probability,
        )
        if not words:
            return Transcript(
                segments=(),
                language=transcript.language,
                duration=max(0.0, end - start),
                source_path=transcript.source_path,
            )
        groups = finalize_display_groups(
            group_words_for_display(
                words,
                words_per_group,
                max_chars_per_line,
            ),
        )
        segments = tuple(
            TranscriptSegment(
                id=i,
                text=group.text,
                start=group.start,
                end=group.end,
                speaker=None,
                words=tuple(group.words),
            )
            for i, group in enumerate(groups)
        )
        return Transcript(
            segments=segments,
            language=transcript.language,
            duration=max(0.0, end - start),
            source_path=transcript.source_path,
        )

    segments = tuple(
        TranscriptSegment(
            id=s.id,
            text=s.text,
            start=s.start,
            end=s.end,
            speaker=s.speaker,
            words=s.words,
        )
        for s in transcript.segments_in_range(start, end)
    )
    return Transcript(
        segments=segments,
        language=transcript.language,
        duration=max(0.0, end - start),
        source_path=transcript.source_path,
    )


def export_srt(transcript: Transcript, out_path: Path) -> Path:
    """Export transcript as an SRT subtitle file."""
    lines: list[str] = []
    for seg in transcript.segments:
        lines.append(str(seg.id + 1))
        lines.append(f"{_fmt_ts(seg.start, ',')} --> {_fmt_ts(seg.end, ',')}")
        lines.append(seg.text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def export_vtt(transcript: Transcript, out_path: Path) -> Path:
    """Export transcript as a WebVTT subtitle file."""
    lines: list[str] = ["WEBVTT", ""]
    for seg in transcript.segments:
        lines.append(f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def export_ttml(transcript: Transcript, out_path: Path) -> Path:
    """Export transcript as a TTML (XML) subtitle file."""
    cues: list[str] = []
    for seg in transcript.segments:
        begin = _fmt_ts(seg.start)
        end = _fmt_ts(seg.end)
        text = escape(seg.text)
        cues.append(f'      <p begin="{begin}" end="{end}">{text}</p>')

    body = "\n".join(cues)
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<tt xml:lang="en" xmlns="http://www.w3.org/ns/ttml">\n'
        "  <head>\n"
        "    <metadata/>\n"
        "    <styling/>\n"
        "    <layout/>\n"
        "  </head>\n"
        "  <body>\n"
        "    <div>\n"
        f"{body}\n"
        "    </div>\n"
        "  </body>\n"
        "</tt>\n"
    )
    out_path.write_text(xml, encoding="utf-8")
    return out_path


def export_ass_content(ass_content: str, out_path: Path) -> Path:
    """Write pre-built ASS subtitle content to disk."""
    out_path.write_text(ass_content, encoding="utf-8")
    return out_path


def export_caption_file(
    transcript: Transcript,
    out_path: Path,
    fmt: CaptionExportFormat,
    *,
    ass_content: str | None = None,
) -> Path:
    """Write ``transcript`` to ``out_path`` in the requested subtitle format."""
    if fmt == "ass":
        if not ass_content:
            raise ValueError("ass_content is required for ASS export")
        return export_ass_content(ass_content, out_path)
    if fmt == "srt":
        return export_srt(transcript, out_path)
    if fmt == "vtt":
        return export_vtt(transcript, out_path)
    return export_ttml(transcript, out_path)


def caption_export_filename(fmt: CaptionExportFormat, *, clip_id: str | None) -> str:
    suffix = f"_{clip_id}" if clip_id else "_full"
    return f"captions{suffix}.{fmt}"
