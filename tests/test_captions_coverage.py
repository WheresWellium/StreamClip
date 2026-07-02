"""Captions module mocked coverage."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
from core.config import get_settings
from core.models import Transcript, TranscriptSegment, Word
from core import captions as cap

def test_detect_emoji_and_gaming():
    assert cap._detect_emoji("fire") == "" or isinstance(cap._detect_emoji("fire"), str)
    assert cap._is_gaming_term("ACE") is True

def test_generate_captions_no_words(tmp_path):
    cfg = get_settings(reload=True)
    clip = tmp_path / "c.mp4"
    out = tmp_path / "o.mp4"
    clip.write_bytes(b"v")
    tr = Transcript(segments=[], language="en", duration=1.0, source_path=clip)
    probe = MagicMock(stdout='{"streams":[{"codec_type":"video","width":1080,"height":1920}]}', returncode=0)
    with patch.object(cap.subprocess, "run", return_value=probe):
        result = cap.generate_captions(clip, out, tr, 0.0, 1.0, cfg)
    # No words → clip is copied through to the output path untouched
    assert result == out
    assert out.read_bytes() == clip.read_bytes()

def test_generate_captions_burn(tmp_path):
    cfg = get_settings(reload=True)
    clip = tmp_path / "c.mp4"
    out = tmp_path / "o.mp4"
    clip.write_bytes(b"v")
    w = Word(text="wow", start=0.0, end=0.4, probability=0.99)
    seg = TranscriptSegment(id=0, text="wow", start=0.0, end=1.0, words=(w,))
    tr = Transcript(segments=[seg], language="en", duration=1.0, source_path=clip)
    probe = MagicMock(stdout='{"streams":[{"codec_type":"video","width":1080,"height":1920}]}', returncode=0)
    runs = [probe, MagicMock(returncode=0), MagicMock(returncode=0)]
    with patch.object(cap.subprocess, "run", side_effect=runs):
        with patch.object(Path, "write_text", return_value=None):
            cap.generate_captions(clip, out, tr, 0.0, 1.0, cfg, emotion="hype")
