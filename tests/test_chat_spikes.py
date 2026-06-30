"""Chat spike detection tests."""

from __future__ import annotations

from core.chat_spikes import ChatEvent, ChatSpikeAnalyser
from core.twitch_chat import parse_twitch_vod_id


def test_parse_twitch_vod_id():
    assert parse_twitch_vod_id("https://www.twitch.tv/videos/1234567890") == "1234567890"
    assert parse_twitch_vod_id("https://example.com/foo") is None


def test_chat_spike_scores_busy_window_higher():
    events = [ChatEvent(offset_secs=float(i % 10), text="hype") for i in range(100)]
    analyser = ChatSpikeAnalyser(events, video_duration=120.0)
    busy = analyser.score(0.0, 10.0)
    quiet = analyser.score(50.0, 60.0)
    assert busy >= quiet


def test_chat_spike_empty_returns_zero():
    analyser = ChatSpikeAnalyser([], video_duration=60.0)
    assert analyser.score(0.0, 10.0) == 0.0
