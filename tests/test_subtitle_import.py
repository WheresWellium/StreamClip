"""SRT/VTT subtitle parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.subtitle_import import find_subtitle_file, parse_srt


def test_parse_srt_valid(tmp_path):
    srt = tmp_path / "test.en.srt"
    srt.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:03,500\n"
        "Hello world\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:06,000\n"
        "Second line\n",
        encoding="utf-8",
    )
    transcript = parse_srt(srt)
    assert transcript is not None
    assert len(transcript.segments) == 2
    assert transcript.segments[0].text == "Hello world"
    assert transcript.duration >= 6.0


def test_parse_srt_no_timestamp(tmp_path):
    srt = tmp_path / "bad.srt"
    srt.write_text("no timestamps here\n\n", encoding="utf-8")
    assert parse_srt(srt) is None


def test_parse_srt_empty_body(tmp_path):
    srt = tmp_path / "empty.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n\n",
        encoding="utf-8",
    )
    assert parse_srt(srt) is None


def test_parse_srt_missing_file(tmp_path):
    assert parse_srt(tmp_path / "missing.srt") is None


def test_parse_srt_os_error(tmp_path, monkeypatch):
    path = tmp_path / "x.srt"
    path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHi\n", encoding="utf-8")

    def boom(_self, *args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(Path, "read_text", boom)
    assert parse_srt(path) is None


def test_find_subtitle_file(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    h = "abc123"
    vtt = cache / f"{h}.en.vtt"
    vtt.write_text("WEBVTT\n", encoding="utf-8")
    assert find_subtitle_file(cache, h) == vtt
    assert find_subtitle_file(cache, "missing") is None

    srt = cache / f"{h}extra.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nx\n", encoding="utf-8")
    assert find_subtitle_file(cache, f"{h}extra") == srt


def test_find_subtitle_file_glob_vtt_only(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    h = "deadbeef"
    loose = cache / f"{h}_auto.vtt"
    loose.write_text("WEBVTT\n", encoding="utf-8")
    assert find_subtitle_file(cache, h) == loose


def test_find_subtitle_file_glob_srt_only(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    h = "cafebabe"
    loose = cache / f"{h}_auto.srt"
    loose.write_text("1\n00:00:01,000 --> 00:00:02,000\nx\n", encoding="utf-8")
    assert find_subtitle_file(cache, h) == loose


def test_parse_srt_skips_bad_timestamp_line(tmp_path):
    srt = tmp_path / "mixed.srt"
    srt.write_text(
        "1\nnot-a-timestamp\nignored\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nvalid\n",
        encoding="utf-8",
    )
    transcript = parse_srt(srt)
    assert transcript is not None
    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "valid"


def test_parse_srt_without_index_line(tmp_path):
    srt = tmp_path / "noindex.srt"
    srt.write_text(
        "00:00:01,000 --> 00:00:02,500\n"
        "Hello there\n",
        encoding="utf-8",
    )
    transcript = parse_srt(srt)
    assert transcript is not None
    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "Hello there"
    assert transcript.segments[0].start == 1.0
    assert transcript.segments[0].end == 2.5


def test_parse_srt_dot_milliseconds(tmp_path):
    srt = tmp_path / "dot.srt"
    srt.write_text(
        "1\n"
        "00:00:01.000 --> 00:00:02.000\n"
        "Dot style\n",
        encoding="utf-8",
    )
    transcript = parse_srt(srt)
    assert transcript is not None
    assert transcript.segments[0].text == "Dot style"


def test_find_subtitle_file_prefers_en_srt(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    h = "hashpref"
    srt = cache / f"{h}.en.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nx\n", encoding="utf-8")
    assert find_subtitle_file(cache, h) == srt
