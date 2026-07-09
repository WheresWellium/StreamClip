"""Finish captions module coverage gaps (style none, clip_transcript, profanity)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import CaptionConfig, Settings
from core.models import Transcript, TranscriptSegment, Word
from core import captions as cap


def test_generate_captions_style_none_copies(tmp_path):
    inp = tmp_path / "clip.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"raw-video")
    cfg = Settings(caption=CaptionConfig(style="none"))
    tr = Transcript(segments=[], language="en", duration=5.0, source_path=inp)
    result = cap.generate_captions(inp, out, tr, 0.0, 5.0, cfg)
    assert result == out
    assert out.read_bytes() == b"raw-video"


def test_generate_captions_uses_clip_transcript(tmp_path):
    inp = tmp_path / "clip.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    w = Word(text="clipword", start=0.0, end=0.5, probability=0.95)
    seg = TranscriptSegment(id=0, text="clipword", start=0.0, end=1.0, words=(w,))
    full = Transcript(segments=[], language="en", duration=60.0, source_path=inp)
    clip_tr = Transcript(segments=[seg], language="en", duration=1.0, source_path=inp)
    cfg = Settings(caption=CaptionConfig(style="gaming_impact", profanity_filter=False))
    probe = MagicMock(stdout='{"streams":[{"codec_type":"video","width":1080,"height":1920}]}', returncode=0)
    with patch.object(cap.subprocess, "run", side_effect=[probe, MagicMock(returncode=0), MagicMock(returncode=0)]):
        with patch.object(Path, "write_text", return_value=None):
            cap.generate_captions(
                inp, out, full, 10.0, 20.0, cfg,
                clip_transcript=clip_tr,
            )


def test_generate_captions_profanity_filter(tmp_path):
    inp = tmp_path / "clip.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    w = Word(text="damn", start=0.0, end=0.4, probability=0.99)
    seg = TranscriptSegment(id=0, text="damn", start=0.0, end=1.0, words=(w,))
    tr = Transcript(segments=[seg], language="en", duration=1.0, source_path=inp)
    cfg = Settings(
        caption=CaptionConfig(
            style="gaming_impact",
            profanity_filter=True,
            profanity_mode="mask",
            profanity_wordlist=tmp_path / "bad.txt",
        )
    )
    (tmp_path / "bad.txt").write_text("damn\n", encoding="utf-8")
    probe = MagicMock(stdout='{"streams":[{"codec_type":"video","width":1080,"height":1920}]}', returncode=0)
    with patch.object(cap.subprocess, "run", side_effect=[probe, MagicMock(returncode=0), MagicMock(returncode=0)]):
        with patch.object(Path, "write_text", return_value=None):
            cap.generate_captions(inp, out, tr, 0.0, 1.0, cfg)


def test_ass_builder_non_gaming_styled_line():
    style = cap._STYLES["gaming_impact"]
    builder = cap._ASSBuilder(style)
    builder.add_line(0.0, 1.0, "hello", emotion="neutral", is_gaming_term=False)
    rendered = builder.render(1080, 1920)
    assert "hello" in rendered
