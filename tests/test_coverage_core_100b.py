"""Line-coverage sweep, part 2 for core/backend leaf helpers and validators
(MASTER_TODO section 3.10 line pillar)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from core.models import Transcript, TranscriptSegment, Word


# ─── caption_timing.py ────────────────────────────────────────────────────────

def test_repair_word_timing_branches():
    from core.caption_timing import repair_word_timing

    # empty token returns unchanged (31)
    blank = Word(text="   ", start=0.0, end=0.0, probability=0.1)
    assert repair_word_timing(blank) is blank

    # too-short duration is stretched to min_duration (37)
    short = Word(text="hi", start=1.0, end=1.02, probability=0.9)
    fixed = repair_word_timing(short, min_duration=0.08)
    assert fixed.end - fixed.start == pytest.approx(0.08)


def test_collect_words_skips_low_prob_and_non_overlapping():
    from core.caption_timing import collect_words_for_window

    seg = TranscriptSegment(
        id=0, text="x", start=0.0, end=10.0,
        words=(
            Word(text="lowprob", start=5.1, end=5.4, probability=0.1),   # skipped (58)
            Word(text="early", start=0.0, end=1.0, probability=0.9),      # non-overlap (60)
            Word(text="keep", start=5.2, end=5.6, probability=0.9),
        ),
    )
    tr = Transcript(segments=[seg], language="en", duration=10.0, source_path=Path("/x"))
    words = collect_words_for_window(tr, 5.0, 6.0, min_probability=0.5)
    assert [w.text for w in words] == ["keep"]


def test_snap_time_to_words_nearby_edges():
    from core.caption_timing import snap_time_to_words

    seg = TranscriptSegment(
        id=0, text="a b c", start=0.0, end=3.0,
        words=(
            Word(text="a", start=0.0, end=0.5, probability=0.9),
            Word(text="b", start=1.0, end=1.5, probability=0.9),
            Word(text="c", start=2.0, end=2.5, probability=0.9),
        ),
    )
    tr = Transcript(segments=[seg], language="en", duration=3.0, source_path=Path("/x"))
    start, end = snap_time_to_words(0.7, 1.8, tr)
    assert start <= end


# ─── distribution/oauth_state.py (39, 44) ─────────────────────────────────────

def test_oauth_state_rejects_wrong_type_and_missing_user():
    import jwt

    from core.config import get_settings
    from core.distribution.oauth_state import verify_oauth_state
    from core.errors import StreamClipError

    cfg = get_settings()
    wrong_type = jwt.encode({"type": "nope", "platform": "tiktok", "sub": "u"},
                            cfg.auth.secret_key, algorithm=cfg.auth.algorithm)
    with pytest.raises(StreamClipError):
        verify_oauth_state(wrong_type, "tiktok", cfg)

    no_user = jwt.encode({"type": "oauth_state", "platform": "tiktok"},
                         cfg.auth.secret_key, algorithm=cfg.auth.algorithm)
    with pytest.raises(StreamClipError):
        verify_oauth_state(no_user, "tiktok", cfg)


# ─── distribution/notify.py (20, 33, 36) ──────────────────────────────────────

def test_webhook_creds_from_none_user():
    from core.distribution.notify import _webhook_creds_from_user

    assert _webhook_creds_from_user(None) == (None, None)


@pytest.mark.asyncio
async def test_resolve_publish_owner_branches():
    from core.distribution.notify import resolve_publish_job_owner_id

    db = MagicMock()
    db.get = AsyncMock(return_value=None)

    clip_job = SimpleNamespace(vault_clip_id=None, clip_id="c1")
    assert await resolve_publish_job_owner_id(db, clip_job) is None  # clip missing (33)

    empty_job = SimpleNamespace(vault_clip_id=None, clip_id=None)
    assert await resolve_publish_job_owner_id(db, empty_job) is None  # neither id (36)


# ─── distribution/credentials.py (58, 73-78) ──────────────────────────────────

def test_managed_env_credentials_branches():
    from core.config import get_settings
    from core.distribution.credentials import _managed_env_credentials

    cfg = get_settings()
    assert isinstance(_managed_env_credentials("tiktok", cfg), tuple)      # 73-77
    assert _managed_env_credentials("unknown-platform", cfg) == ("", "")   # 78


@pytest.mark.asyncio
async def test_resolve_oauth_app_env_fallback(monkeypatch):
    import core.distribution.credentials as creds_mod
    from core.config import get_settings

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.distribution, "mode", "byo")
    monkeypatch.setattr(cfg.distribution, "youtube_client_id", "cid")
    monkeypatch.setattr(cfg.distribution, "youtube_client_secret", "csecret")

    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)  # no BYO row -> env fallback (56-58)
    monkeypatch.setattr(creds_mod, "InstallOAuthAppRepository", lambda db: repo)

    result = await creds_mod.resolve_oauth_app(MagicMock(), "youtube_shorts", cfg=cfg)
    assert result.client_id == "cid"


# ─── commerce helpers (entitlements 14, lemon_squeezy 42) ─────────────────────

def test_audio_variant_ids_empty():
    from core.commerce.entitlements import _audio_variant_ids
    from core.config import get_settings

    cfg = get_settings(reload=True)
    cfg.commerce.audio_ingest_variant_ids = ""
    assert _audio_variant_ids(cfg) == set()


def test_parse_order_event_variant_from_first_item():
    from core.commerce.lemon_squeezy import parse_order_event

    parsed = parse_order_event({
        "meta": {"event_name": "order_created"},
        "data": {"id": "o1", "attributes": {"first_order_item": {"variant_id": 42}}},
    })
    assert parsed["variant_id"] == "42"


# ─── distribution/registry.py (48) ────────────────────────────────────────────

def test_list_platforms_skips_disabled_tiktok(monkeypatch):
    from core.config import get_settings
    from core.distribution.registry import list_platforms

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.distribution, "tiktok_publish_enabled", False)
    ids = {p.id for p in list_platforms()}
    assert "tiktok" not in ids


# ─── gpu_profile.py (122-123) ─────────────────────────────────────────────────

def test_apply_gpu_env_defaults_mps_requested_without_hw(monkeypatch):
    import core.gpu_profile as gp

    monkeypatch.setattr(gp, "cuda_available", lambda: False)
    monkeypatch.setattr(gp, "mps_available", lambda: False)
    monkeypatch.setattr(gp, "nvenc_available", lambda cfg=None: False)
    monkeypatch.setenv("STREAMCLIP_WHISPER__DEVICE", "mps")
    gp.apply_gpu_env_defaults()
    assert os.environ["STREAMCLIP_WHISPER__DEVICE"] == "cpu"


# ─── ffmpeg_bins.py (34) ──────────────────────────────────────────────────────

def test_app_root_frozen(monkeypatch):
    import core.ffmpeg_bins as fb

    monkeypatch.delenv("STREAMCLIP_APP_ROOT", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/opt/app/streamclip.exe", raising=False)
    root = fb.app_root()
    assert str(root).endswith("app")


# ─── static_ui.py (44) ────────────────────────────────────────────────────────

def test_resolve_static_dir_missing_dir(monkeypatch):
    from backend.static_ui import resolve_static_dir
    from core.config import get_settings

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", True)
    monkeypatch.setattr(cfg.web, "static_dir", "/nonexistent-static-xyz")
    assert resolve_static_dir(cfg) is None


# ─── schemas.py validators ────────────────────────────────────────────────────

def test_create_job_request_validators():
    from backend.api.schemas import CreateJobRequest

    # None source_url / display_title pass through their validators (62, 98)
    ok = CreateJobRequest(source_url=None, display_title=None)
    assert ok.source_url is None

    for field, value in (
        ("caption_style", "bogus"),      # 71
        ("reframe_preset", "bogus"),     # 85
        ("content_profile", "bogus"),    # 92
    ):
        with pytest.raises(ValidationError):
            CreateJobRequest(**{field: value})


def test_update_job_request_display_title_none():
    from backend.api.schemas import UpdateJobRequest

    assert UpdateJobRequest(display_title=None).display_title is None  # 186


def test_beta_feedback_request_environment_ok():
    from backend.api.schemas import BetaFeedbackRequest

    body = BetaFeedbackRequest(topic="idea", message="hello world here", environment={"a": "b"})
    assert body.environment == {"a": "b"}  # 453


def test_update_clip_request_validators():
    from backend.api.schemas import UpdateClipRequest

    # valid transcript edits pass through
    assert UpdateClipRequest(transcript_edits={"0": "hi"}).transcript_edits == {"0": "hi"}

    with pytest.raises(ValidationError):
        UpdateClipRequest(transcript_edits={str(i): "x" for i in range(501)})  # 537
    with pytest.raises(ValidationError):
        UpdateClipRequest(caption_style="bogus")   # 551
    with pytest.raises(ValidationError):
        UpdateClipRequest(reframe_preset="bogus")  # 558
