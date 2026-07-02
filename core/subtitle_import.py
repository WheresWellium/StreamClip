"""SRT/VTT subtitle parsing for ingest → transcribe seeding."""

from __future__ import annotations

import re
from pathlib import Path

from core.models import Transcript, TranscriptSegment, Word


_TS = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})",
)


def _parse_ts(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: Path) -> Transcript | None:
    """Parse an SRT file into a Transcript. Returns None if parse fails."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    segments: list[TranscriptSegment] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    seg_id = 0
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        ts_line = lines[1] if lines[0].isdigit() else lines[0]
        body_lines = lines[2:] if lines[0].isdigit() else lines[1:]
        m = _TS.search(ts_line)
        if not m:
            continue
        start = _parse_ts(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _parse_ts(m.group(5), m.group(6), m.group(7), m.group(8))
        body = " ".join(body_lines).strip()
        if not body:
            continue
        words = tuple(
            Word(text=w, start=start, end=end, probability=0.85)
            for w in body.split()
        )
        segments.append(
            TranscriptSegment(id=seg_id, text=body, start=start, end=end, words=words),
        )
        seg_id += 1

    if not segments:
        return None
    duration = max(s.end for s in segments)
    return Transcript(
        segments=segments,
        language="en",
        duration=duration,
        source_path=path,
    )


def find_subtitle_file(cache_dir: Path, url_hash: str) -> Path | None:
    """Locate yt-dlp subtitle file next to cached video."""
    for ext in (".en.vtt", ".en.srt", ".vtt", ".srt"):
        candidate = cache_dir / f"{url_hash}{ext}"
        if candidate.exists():
            return candidate
    for path in cache_dir.glob(f"{url_hash}*.vtt"):
        return path
    for path in cache_dir.glob(f"{url_hash}*.srt"):
        return path
    return None
