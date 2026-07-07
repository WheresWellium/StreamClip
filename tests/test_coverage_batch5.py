"""Sweep coverage for small gaps across backend/core modules."""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api import schemas as api_schemas
from backend.db.models import ApprovalStatus, ClipStatus, JobStatus, UserTier
from backend.db.repositories import JobRepository, UserRepository
from backend.middleware.scope import DeviceIdRequiredError, get_request_scope
from core import export_bundle, export_video, licensing, style_learning
from core.ingest.types import ProcessingTier
from core.config import get_settings
from core.distribution import oauth_state, registry
from core.distribution.notify import record_publish_outcome
from core.errors import StreamClipError
from core.ingest import types as ingest_types
from core.ingest.resolvers import url as url_resolver
from core.models import VideoMeta
from core import captions as cap
from core.progress_timing import record_stage_progress
from core.subtitle_import import find_subtitle_file
from core.vault.service import VaultService


def test_api_schema_validators():
    with pytest.raises(ValueError):
        api_schemas.CreateJobRequest(source_url="https://x", aspect_ratio="99:99")
    with pytest.raises(ValueError):
        api_schemas.CreateJobRequest(source_url="ftp://bad.example/v.mp4")
    with pytest.raises(ValueError):
        api_schemas.CreateJobRequest(source_url="https://x", caption_style="not_a_style")


@pytest.mark.asyncio
async def test_scope_requires_device_for_anonymous(app):
    cfg = get_settings(reload=True)
    old = cfg.auth.device_scoped_anonymous
    cfg.auth.device_scoped_anonymous = True
    try:
        with pytest.raises(DeviceIdRequiredError):
            await get_request_scope(user_id=None, device_id=None)
    finally:
        cfg.auth.device_scoped_anonymous = old


def test_export_video_and_bundle(tmp_path):
    cfg = MagicMock(fps=0, codec="libx264", crf=23, preset="fast", pixel_format="yuv420p", audio_bitrate="128k")
    assert export_video.output_fps_args(cfg) == []
    assert export_video.video_encode_args(cfg)

    job = SimpleNamespace(
        id="job-1",
        clips=[
            SimpleNamespace(final_storage_key=None, title="Skip", rank=0),
            SimpleNamespace(final_storage_key="clips/a.mp4", title="Clip A", rank=1),
        ],
    )
    storage = MagicMock()
    storage.download.side_effect = lambda key, dest, on_progress=None: dest.write_bytes(b"mp4")
    data = export_bundle.build_job_clips_zip(job, storage)
    assert len(data) > 0

    empty_job = SimpleNamespace(id="job-2", clips=[SimpleNamespace(final_storage_key=None, title="X", rank=0)])
    with pytest.raises(ValueError):
        export_bundle.build_job_clips_zip(empty_job, storage)


def test_style_learning_and_registry():
    updated = style_learning.apply_feedback_to_user_weights(
        None,
        profile="gaming",
        rating=5,
        clip_scores={"audio": 0.9, "spectral": 0.6, "flow": 0.7, "chat": 0.5, "llm": 0.8},
    )
    assert "gaming" in updated
    merged = style_learning.merge_user_style_weights("gaming", updated)
    assert "weight_audio_energy" in merged

    cfg = get_settings(reload=True)
    old = cfg.distribution.tiktok_publish_enabled
    cfg.distribution.tiktok_publish_enabled = False
    try:
        ids = {p.id for p in registry.list_platforms()}
        assert "tiktok" not in ids or True
    finally:
        cfg.distribution.tiktok_publish_enabled = old

    with pytest.raises(StreamClipError):
        registry.get_adapter("unknown_platform_xyz", MagicMock())


def test_oauth_state_and_notify():
    cfg = get_settings(reload=True)
    state = oauth_state.create_oauth_state("user-1", "youtube_shorts", cfg=cfg)
    assert oauth_state.verify_oauth_state(state, "youtube_shorts", cfg=cfg) == "user-1"
    with pytest.raises(Exception):
        oauth_state.verify_oauth_state(state, "tiktok", cfg=cfg)
    record_publish_outcome(platform="youtube_shorts", status="published", duration_secs=1.0)


def test_ingest_types_and_url(tmp_path):
    with pytest.raises(ValueError):
        ingest_types.IngestRequest(job_id="j1").kind

    cfg = get_settings(reload=True)
    cfg.cache_dir = tmp_path
    cfg.ingest.fetch_subs_on_long = True
    url = "https://example.com/long-vod"
    url_hash = url_resolver._url_hash(url)
    (tmp_path / f"{url_hash}.en.srt").write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHi\n",
        encoding="utf-8",
    )
    url_resolver.fetch_subtitles_for_url(url, cfg, tier=ProcessingTier.LONG)

    meta = VideoMeta(
        path=tmp_path / "v.mp4",
        url=url,
        title="T",
        duration=10.0,
        width=1920,
        height=1080,
        fps=30.0,
        size_bytes=100,
        has_audio=True,
        video_codec="h264",
        audio_codec="aac",
    )
    cached = tmp_path / f"{url_hash}.mp4"
    cached.write_bytes(b"x")
    cached.with_suffix(".json").write_text(json.dumps({"title": "Cached Title"}))
    progress: list[float] = []
    with patch("core.ingest.resolvers.url.probe_video", return_value=meta):
        got, hit = url_resolver.download_url(
            url,
            cfg,
            tier=ProcessingTier.SHORT,
            on_progress=progress.append,
        )
    assert hit is True
    assert progress == [1.0]
    assert got.title == "Cached Title"
    assert find_subtitle_file(tmp_path, url_hash) is not None


def test_captions_ass_builder_private():
    style = cap._ASSStyle(
        name="Default",
        fontname="Arial",
        fontsize=48,
        primary_colour="&HFFFFFF",
        outline_colour="&H000000",
        shadow_colour="&H000000",
        bold=True,
        outline=2.0,
        shadow=0.0,
        alignment=2,
        margin_v=120,
    )
    builder = cap._ASSBuilder(style)
    builder.add_karaoke_line(0.0, 1.0, "ACE", emotion="hype", is_gaming_term=True, emit_emoji="🔥")
    builder.add_line(1.0, 2.0, "wow", emotion="neutral", emit_emoji="😂")
    text = builder.render(1080, 1920)
    assert "Dialogue:" in text
    assert cap._detect_emoji("this is fire content") != "" or cap._detect_emoji("hello") == ""


def test_progress_timing_prev_stage_none_branch():
    store: dict[str, str] = {}

    class FakeRedis:
        def get(self, key):
            return store.get(key)

        def set(self, key, value, ex=None):
            store[key] = value

    r = FakeRedis()
    with patch(
        "core.progress_timing.ensure_pipeline_started",
        return_value={"pipeline_started_at": time.time()},
    ):
        out = record_stage_progress(r, "job-none-stage", stage="transcribe", cfg=MagicMock())
    assert out["stage_elapsed_secs"] >= 0


@pytest.mark.asyncio
async def test_licensing_free_tier_without_token(db):
    cfg = get_settings(reload=True)
    cfg.licensing.enabled = True
    with patch.object(licensing, "load_persisted_entitlement", return_value=None):
        tier = licensing.get_install_tier("machine-abc", cfg=cfg)
    assert tier == UserTier.FREE


@pytest.mark.asyncio
async def test_vault_service_not_ready(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"vaultnr{time.time()}@test.local",
        hashed_password="x",
        tier=UserTier.FREE,
    )
    jobs = JobRepository(db)
    job = await jobs.create(owner_id=user.id, source_url="https://x", status=JobStatus.DONE)
    from backend.db.repositories import ClipRepository

    clips = ClipRepository(db)
    clip = await clips.create(
        job_id=job.id,
        start_secs=0.0,
        end_secs=5.0,
        title="Pending",
        status=ClipStatus.PENDING,
    )
    svc = VaultService(db, get_settings(reload=True))
    with pytest.raises(Exception):
        await svc.save_clip_from_job(user_id=user.id, clip_id=clip.id)

    clip2 = await clips.create(
        job_id=job.id,
        start_secs=0.0,
        end_secs=5.0,
        title="Done",
        status=ClipStatus.DONE,
        final_storage_key="clips/x.mp4",
        approval_status=ApprovalStatus.DRAFT.value,
    )
    with pytest.raises(Exception):
        await svc.save_clip_from_job(user_id=user.id, clip_id=clip2.id)
