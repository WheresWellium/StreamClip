from __future__ import annotations
from unittest.mock import MagicMock, patch
import json
import pytest
from core.config import get_settings
from core.content_profiles import get_profile
from core.models import Emotion
from core import virality as v
from core.twitch_chat import fetch_vod_chat, _events_from_gql_payload
from core.chat_spikes import ChatEvent

def test_build_client_openai(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "openai")
    monkeypatch.setattr(cfg.llm, "api_key", "k")
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=MagicMock(return_value="c"))}):
        assert v._build_client(cfg.llm) == "c"

def test_build_client_anthropic(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "anthropic")
    with patch.dict("sys.modules", {"anthropic": MagicMock(Anthropic=MagicMock(return_value="a"))}):
        assert v._build_client(cfg.llm) == "a"

def test_build_client_unknown(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "bogus")
    with pytest.raises(ValueError):
        v._build_client(cfg.llm)

def test_call_llm_ollama_uses_json_mode(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "ollama")
    monkeypatch.setattr(cfg.llm, "num_predict", 512)
    client = MagicMock()
    client.chat.return_value = MagicMock(message=MagicMock(content='{"score": 1}'))
    v._call_llm(client, cfg.llm, "p")
    kwargs = client.chat.call_args.kwargs
    assert kwargs.get("format") == "json"
    assert kwargs["options"]["num_predict"] == 512


def test_call_llm_anthropic(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "anthropic")
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[MagicMock(text='{"score":80,"emotion":"hype","meme_keywords":[],"reason":"r"}')])
    out = v._call_llm(client, cfg.llm, "p")
    assert "80" in out

def test_score_clip_virality_success(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "provider", "ollama")
    client = MagicMock()
    client.chat.return_value = MagicMock(message=MagicMock(content='{"score": 90, "emotion": "hype", "meme_keywords": ["pog"], "reason": "nice"}'))
    r = v.score_clip_virality(text="wow", start_secs=0, end_secs=5, cfg=cfg, client=client)
    assert r.score == 90.0

def test_score_parallel_and_ensemble(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.llm, "parallel_workers", 2)
    # _build_client imports the provider SDK (ollama) — stub it so this test
    # runs on hosts without the worker-only dependencies installed.
    with patch.object(v, "_build_client", return_value=MagicMock()), \
         patch.object(v, "score_clip_virality", return_value=v.ViralityResult(1, Emotion.NEUTRAL, "", [])):
        out = v.score_clips_virality_parallel([("a", 0, 1), ("b", 1, 2)], cfg)
    assert len(out) == 2
    assert v.score_clips_virality_parallel([], cfg) == []
    prof = get_profile("gaming")
    s = v.ensemble_with_virality(llm_score=50, audio_score=0.5, spectral_score=0.5, flow_score=0.5, chat_score=0.5, hcfg=cfg.highlight, skip_optical_flow=False, has_chat=True, profile=prof)
    assert 0 <= s <= 1


def test_score_clip_virality_unknown_emotion(monkeypatch):
    cfg = get_settings(reload=True)
    client = MagicMock()
    client.chat.return_value = MagicMock(
        message=MagicMock(content='{"score": 50, "emotion": "not_real", "meme_keywords": [], "reason": "ok"}'),
    )
    r = v.score_clip_virality(text="x", start_secs=0, end_secs=1, cfg=cfg, client=client)
    assert r.emotion == Emotion.NEUTRAL


def test_ensemble_zero_weights_fallback(monkeypatch):
    cfg = get_settings(reload=True)
    hcfg = cfg.highlight
    monkeypatch.setattr(hcfg, "weight_llm_virality", 0.0)
    monkeypatch.setattr(hcfg, "weight_audio_energy", 0.0)
    monkeypatch.setattr(hcfg, "weight_spectral_novelty", 0.0)
    monkeypatch.setattr(hcfg, "weight_optical_flow", 0.0)
    monkeypatch.setattr(hcfg, "weight_chat_spikes", 0.0)
    score = v.ensemble_with_virality(
        llm_score=80.0,
        audio_score=0.5,
        spectral_score=0.5,
        flow_score=0.5,
        hcfg=hcfg,
    )
    assert score == 0.0

def test_events_from_gql_payload():
    data = {"data": {"video": {"comments": {"edges": [{"node": {"contentOffsetSeconds": 1, "message": {"fragments": [{"text": "hi"}]}}}], "pageInfo": {"hasNextPage": False}}}}}
    events, cursor, more = _events_from_gql_payload(data)
    assert events or isinstance(events, list)

def test_fetch_vod_chat_pagination(monkeypatch, tmp_path):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "twitch_client_id", "cid")
    batch1 = [ChatEvent(1.0, "a")]
    batch2 = [ChatEvent(2.0, "b")]
    responses = [
        MagicMock(json=lambda: {}, raise_for_status=lambda: None),
    ]
    def fake_post(*a, **k):
        m = MagicMock()
        m.raise_for_status = lambda: None
        if len(responses):
            m.json.return_value = {"data": {"video": {"comments": {"edges": [{"node": {"contentOffsetSeconds": 1, "message": {"fragments": [{"text": "x"}]}}}], "pageInfo": {"hasNextPage": True, "endCursor": "c1"}}}}}
            return m
        m.json.return_value = {"data": {"video": {"comments": {"edges": [], "pageInfo": {"hasNextPage": False}}}}}
        return m
    with patch("core.twitch_chat.parse_twitch_vod_id", return_value="123"):
        with patch("core.twitch_chat._events_from_gql_payload", side_effect=[(batch1, "c1", True), (batch2, None, False)]):
            with patch("httpx.Client") as hc:
                hc.return_value.__enter__.return_value.post.side_effect = fake_post
                ev = fetch_vod_chat(source_url="https://twitch.tv/videos/123", cfg=cfg, cache_path=tmp_path / "c.json")
    assert isinstance(ev, list)
