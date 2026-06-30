"""Core datamodel tests."""

from __future__ import annotations

from core.models import Emotion, SignalScores, TranscriptSegment


def test_signal_scores_ensemble():
    s = SignalScores(llm_virality=0.5, audio_energy=0.5, spectral_novelty=0.0, optical_flow=0.0, chat_spikes=0.0)
    s.set_ensemble(0.75)
    assert s.ensemble == 0.75


def test_transcript_segment_duration():
    seg = TranscriptSegment(id=0, text="hi", start=1.0, end=3.5, words=())
    assert seg.duration == 2.5


def test_emotion_enum():
    assert Emotion.HYPE.value == "hype"
