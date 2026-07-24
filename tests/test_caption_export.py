"""Tests for core.caption_export — subtitle file generation."""

from __future__ import annotations

from pathlib import Path

from core.caption_export import (
    build_export_transcript,
    export_caption_file,
    export_srt,
    export_ttml,
    export_vtt,
)
from core.models import Transcript, TranscriptSegment, Word


def _sample_transcript() -> Transcript:
    return Transcript(
        segments=(
            TranscriptSegment(
                id=0,
                text="hello world",
                start=0.0,
                end=2.0,
                speaker=None,
                words=(
                    Word(text="hello", start=0.0, end=0.8, probability=0.95),
                    Word(text="world", start=0.9, end=2.0, probability=0.90),
                ),
            ),
            TranscriptSegment(
                id=1,
                text="second line",
                start=2.5,
                end=4.0,
                speaker=None,
                words=(
                    Word(text="second", start=2.5, end=3.2, probability=0.88),
                    Word(text="line", start=3.3, end=4.0, probability=0.91),
                ),
            ),
        ),
        language="en",
        duration=4.0,
        source_path=Path("source.mp4"),
    )


def test_build_export_transcript_word_level_groups(tmp_path: Path):
    tx = _sample_transcript()
    export_tx = build_export_transcript(
        tx,
        word_level=True,
        words_per_group=2,
        max_chars_per_line=40,
        min_probability=0.25,
    )
    assert len(export_tx.segments) >= 1
    assert export_tx.segments[0].text  # grouped uppercase text


def test_build_export_transcript_segment_level(tmp_path: Path):
    tx = _sample_transcript()
    export_tx = build_export_transcript(tx, word_level=False)
    assert len(export_tx.segments) == 2
    assert export_tx.segments[0].text == "hello world"


def test_build_export_transcript_clip_window(tmp_path: Path):
    tx = _sample_transcript()
    export_tx = build_export_transcript(
        tx,
        window_start=2.0,
        window_end=4.5,
        word_level=False,
    )
    assert len(export_tx.segments) == 1
    assert export_tx.segments[0].text == "second line"


def test_export_srt_vtt_ttml(tmp_path: Path):
    tx = _sample_transcript()
    export_tx = build_export_transcript(tx, word_level=False)

    srt_path = tmp_path / "out.srt"
    export_srt(export_tx, srt_path)
    srt_text = srt_path.read_text(encoding="utf-8")
    assert "hello world" in srt_text
    assert "-->" in srt_text

    vtt_path = tmp_path / "out.vtt"
    export_vtt(export_tx, vtt_path)
    vtt_text = vtt_path.read_text(encoding="utf-8")
    assert vtt_text.startswith("WEBVTT")
    assert "hello world" in vtt_text

    ttml_path = tmp_path / "out.ttml"
    export_ttml(export_tx, ttml_path)
    ttml_text = ttml_path.read_text(encoding="utf-8")
    assert "<tt " in ttml_text
    assert "hello world" in ttml_text


def test_export_caption_file_dispatches(tmp_path: Path):
    tx = build_export_transcript(_sample_transcript(), word_level=False)
    out = tmp_path / "captions.vtt"
    export_caption_file(tx, out, "vtt")
    assert out.exists()


def test_export_ass_content(tmp_path: Path):
    tx = build_export_transcript(_sample_transcript(), word_level=False)
    out = tmp_path / "captions.ass"
    export_caption_file(tx, out, "ass", ass_content="[Script Info]\nTitle: test\n")
    text = out.read_text(encoding="utf-8")
    assert "Script Info" in text
