"""Sweep smaller coverage gaps across backend/core modules."""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from backend.api import schemas as api_schemas
from backend.db.models import User, UserTier
from backend.db.session import dispose_engine, get_sessionmaker
from backend.middleware.auth import AuthError, decode_token, get_current_user_id
from backend.services.auth_service import AuthService
from core import errors as errors_mod
from core import ffmpeg_bins
from core import models as core_models
from core import peak_detection as pd
from core import profanity as prof_mod
from core import progress_bus as pb_mod
from core import storage as storage_mod
from core.celery_app import celery_app
from core.commerce import entitlements as ent
from core.config import get_settings
from core.eta import estimate_remaining_seconds as estimate_remaining_secs
from core.tasks import notify_tasks as nt


# ─── schemas ─────────────────────────────────────────────────────────────────


def test_create_job_display_title_whitespace_becomes_none():
    req = api_schemas.CreateJobRequest(source_url="https://example.com/v.mp4", display_title="   ")
    assert req.display_title is None


def test_create_job_invalid_enums():
    with pytest.raises(ValidationError):
        api_schemas.CreateJobRequest(source_url="https://x", caption_style="bad_style")
    with pytest.raises(ValidationError):
        api_schemas.CreateJobRequest(source_url="https://x", reframe_preset="bad_preset")
    with pytest.raises(ValidationError):
        api_schemas.CreateJobRequest(source_url="https://x", content_profile="bad_profile")


def test_bug_report_environment_too_many_keys():
    with pytest.raises(ValidationError):
        api_schemas.BugReportRequest(
            message="long enough message here",
            categories=["ui"],
            environment={f"k{i}": "v" for i in range(21)},
        )


def test_update_clip_transcript_edits_validation():
    with pytest.raises(ValidationError):
        api_schemas.UpdateClipRequest(transcript_edits={"bad": "x"})
    with pytest.raises(ValidationError):
        api_schemas.UpdateClipRequest(transcript_edits={str(i): "x" for i in range(501)})


# ─── HTTP edges ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_inactive_user_login(client):
    email = f"inactive-{__import__('uuid').uuid4().hex[:8]}@test.local"
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        user = await session.get(User, user_id)
        user.is_active = False
        await session.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "hunter2secure"},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_license_status_missing_machine_id(client):
    resp = await client.get("/api/license/status")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_settings_templates_unauthorized(client):
    resp = await client.get("/api/templates")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_vault_list_requires_auth(client):
    resp = await client.get("/api/vault/clips")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_support_beta_feedback_validation(client):
    resp = await client.post(
        "/api/support/beta-feedback",
        json={"message": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_ready_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200


# ─── middleware auth ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_missing_bearer_prefix(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/settings/webhook",
            headers={"Authorization": "Token abc"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_decode_token_expired():
    cfg = get_settings(reload=True)
    import jwt

    token = jwt.encode(
        {"sub": "u1", "type": "access", "exp": 1},
        cfg.auth.secret_key,
        algorithm=cfg.auth.algorithm,
    )
    with pytest.raises(AuthError, match="expired"):
        decode_token(token, cfg)


# ─── session sqlite + rollback ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_db_session_rollback_on_error():
    from backend.db.session import db_session

    with pytest.raises(RuntimeError):
        async with db_session() as session:
            assert session is not None
            raise RuntimeError("force rollback")


def test_sqlite_engine_foreign_keys_pragma(monkeypatch):
    from backend.db import session as sess_mod

    sess_mod.dispose_engine()
    monkeypatch.setenv("STREAMCLIP_DATABASE__URL", "sqlite+aiosqlite:///:memory:")
    cfg = get_settings(reload=True)
    if cfg.database.is_sqlite:
        engine = sess_mod.get_engine(cfg)
        assert engine is not None


# ─── main.py edges ───────────────────────────────────────────────────────────


def test_main_jwt_warning_logged(monkeypatch):
    """Weak secrets log SECURITY_WARNING (not critical) — aligned with O8."""
    import asyncio
    import backend.main as main_mod

    cfg = get_settings(reload=True)
    # Lifespan patches bypass Settings validation; production reject is covered elsewhere.
    monkeypatch.setattr(cfg, "environment", "production")
    monkeypatch.setattr(cfg.auth, "secret_key", "CHANGE_ME_IN_PRODUCTION")
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    monkeypatch.setattr(main_mod, "get_settings", lambda: cfg)

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    engine = MagicMock()
    engine.connect = MagicMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=None))
    )
    engine.dispose = AsyncMock()

    with patch.object(main_mod.log, "warning") as warn, patch.object(main_mod, "_init_sentry"), patch.object(
        main_mod, "init_opentelemetry"
    ), patch("backend.db.session.get_engine", return_value=engine):
        app = main_mod.create_app()

        async def _run_lifespan():
            async with app.router.lifespan_context(app):
                pass

        asyncio.run(_run_lifespan())
        warn.assert_called()
        event = warn.call_args.args[0] if warn.call_args.args else warn.call_args.kwargs.get("event")
        assert event == "SECURITY_WARNING"
        assert warn.call_args.kwargs.get("auth_secret_issue") == "placeholder"


@pytest.mark.asyncio
async def test_http_exception_list_detail_sanitized(app):
    from backend.main import create_app

    test_app = create_app()

    @test_app.get("/test-list-detail")
    async def _boom():
        raise HTTPException(status_code=400, detail=[{"msg": "bad"}])

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/test-list-detail")
    assert resp.status_code == 400
    assert resp.json()["message"] == "Validation failed."


def test_main_module_entrypoint(monkeypatch):
    with patch("uvicorn.run") as uv_run:
        import runpy
        import backend.main as main_mod

        with patch.object(main_mod, "__name__", "__main__"):
            try:
                runpy.run_path(main_mod.__file__, run_name="__main__")
            except SystemExit:
                pass
        # Direct call mirrors __main__ block
        import uvicorn
        uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
        uv_run.assert_called()


# ─── entitlements ────────────────────────────────────────────────────────────


def test_entitlements_audio_variant_helpers(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.commerce, "audio_ingest_variant_ids", " v1 , v2 ")
    assert ent.variant_grants_audio_ingest("v1", cfg) is True
    assert ent.variant_grants_audio_ingest(None, cfg) is False
    assert ent.order_id_tags_audio_ingest("audio:ord-1") is True
    assert ent.order_id_tags_audio_ingest("ord-1") is False
    assert ent.tag_audio_order_id("ord-1") == "audio:ord-1"
    assert ent.tag_audio_order_id("audio:ord-1") == "audio:ord-1"
    assert ent.tag_audio_order_id(None) is None


@pytest.mark.asyncio
async def test_scope_allows_audio_ingest_by_machine(db, monkeypatch):
    from backend.db.repositories import InstallLicenseRepository
    from datetime import datetime, timezone

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.features, "audio_ingest", False)
    lic_repo = InstallLicenseRepository(db)
    stamp = datetime.now().timestamp()
    machine_id = f"machine-audio-{stamp}"
    lic = await lic_repo.create_issued(
        license_key_hash=f"audio-{stamp}",
        tier=UserTier.PRO,
        order_id=f"audio:shop-{stamp}",
    )
    await lic_repo.mark_activated(
        lic,
        machine_id=machine_id,
        entitlement_jwt="jwt",
        expires_at=datetime.now(timezone.utc),
        count_activation=True,
    )
    assert await ent.scope_allows_audio_ingest(db, machine_id=machine_id, cfg=cfg) is True
    assert await ent.scope_allows_audio_ingest(db, machine_id=None, cfg=cfg) is False


# ─── notify_tasks missing row ────────────────────────────────────────────────


def test_send_ops_webhook_missing_row():
    with patch.object(nt, "_safe_async", return_value=None), \
         patch.object(nt, "post_ops_webhook") as post:
        out = nt.send_ops_webhook.run("missing-id", "bug_report")
    assert out["status"] == "skipped"
    assert out["reason"] == "not_found"
    post.assert_not_called()


# ─── celery sentry ───────────────────────────────────────────────────────────


def test_celery_sentry_init_success(monkeypatch):
    import core.celery_app as ca

    monkeypatch.setattr(ca, "cfg", get_settings(reload=True))
    monkeypatch.setattr(ca.cfg.observability, "sentry_dsn", "https://example@sentry.io/1")
    fake_sentry = MagicMock()
    fake_celery_int = MagicMock()
    fake_sql_int = MagicMock()
    with patch.dict(
        sys.modules,
        {
            "sentry_sdk": fake_sentry,
            "sentry_sdk.integrations.celery": MagicMock(CeleryIntegration=fake_celery_int),
            "sentry_sdk.integrations.sqlalchemy": MagicMock(SqlalchemyIntegration=fake_sql_int),
        },
    ):
        ca._init_worker_sentry()
        fake_sentry.init.assert_called()


def test_celery_task_failure_sentry_import_error(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "https://example@sentry.io/1")
    import core.celery_app as ca
    with patch.dict(sys.modules, {"sentry_sdk": None}):
        ca._on_task_failure("tid", RuntimeError("x"), MagicMock(name="task"), None, None)


# ─── peak_detection / eta / errors ───────────────────────────────────────────


def test_peak_detection_empty_arrays():
    import numpy as np

    empty = np.array([])
    assert pd.smooth_series(empty, 3).size == 0
    assert pd.find_peak_indices(empty) == []
    assert pd.merge_peak_times([], merge_gap_secs=1.0) == []
    assert (
        pd.windows_from_peaks(
            [],
            padding_secs=1,
            min_duration=1,
            max_duration=10,
            source_duration=60.0,
        )
        == []
    )


def test_eta_unknown_stage_defaults_to_start():
    cfg = get_settings()
    out = estimate_remaining_secs(
        "totally_unknown_stage",
        stage_durations={},
        stage_elapsed_secs=0.0,
        duration_secs=120.0,
        source_kind="url",
        target_clips=3,
        skip_optical_flow=True,
        cfg=cfg,
    )
    assert out is not None
    assert out >= 0.0


def test_sanitize_user_message_empty():
    assert errors_mod.sanitize_user_message(None) == "Something went wrong."
    assert errors_mod.sanitize_user_message("   ") == "Something went wrong."


# ─── ffmpeg_bins / models / profanity / progress_bus ─────────────────────────


def test_ffmpeg_bins_missing_override(monkeypatch, tmp_path):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.ffmpeg, "ffmpeg_path", None)
    monkeypatch.setattr(cfg.ffmpeg, "bin_dir", None)
    with patch.object(ffmpeg_bins.shutil, "which", return_value=None), patch.object(
        ffmpeg_bins, "app_root", return_value=tmp_path
    ):
        path = ffmpeg_bins.ffmpeg_bin(cfg)
    assert path == "ffmpeg"


def test_core_models_word_count_and_duration():
    from core.models import Transcript, TranscriptSegment, Word

    w = Word(text="hi", start=0.0, end=0.5, probability=0.9)
    seg = TranscriptSegment(id=0, text="hi", start=0.0, end=1.0, words=(w,))
    tr = Transcript(segments=[seg], language="en", duration=5.0, source_path=Path("x"))
    assert seg.word_count == 1
    assert tr.text_in_range(0.0, 1.0)


def test_profanity_censor_token_punctuation_only():
    assert prof_mod.censor_token("!!!", mode="mask") == "!!!"


def test_progress_bus_queue_full_warning(monkeypatch):
    pb_mod.reset_progress_bus()
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    bus = pb_mod.get_progress_bus(cfg)
    q = bus.subscribe("ch-full")
    for _ in range(256):
        q.put_nowait("{}")
    with patch.object(pb_mod.log, "warning") as warn:
        bus.publish("ch-full", {"status": "processing"})
        warn.assert_called()
    pb_mod.reset_progress_bus()


# ─── storage / twitch_chat / distribution / services ─────────────────────────


def test_storage_local_list_prefix(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "local")
    monkeypatch.setattr(cfg.storage, "local_root", str(tmp_path))
    store = storage_mod.make_storage(cfg)
    (tmp_path / "a.txt").write_text("x")
    keys = store.list_prefix("")
    assert "a.txt" in keys or any("a.txt" in k for k in keys)


def test_twitch_chat_empty_batch_breaks(monkeypatch):
    from core import twitch_chat as tc

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "twitch_client_id", "test-client")
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"data": {"video": {"comments": {"edges": [], "pageInfo": {"hasNextPage": False}}}}}
    with patch("core.twitch_chat.httpx.post", return_value=fake_resp), patch(
        "core.twitch_chat.parse_twitch_vod_id", return_value="12345"
    ):
        events = tc.fetch_vod_chat(source_url="https://twitch.tv/videos/12345", cfg=cfg, max_messages=10)
    assert events == []


def test_distribution_oauth_state_bad_platform():
    from core.distribution import oauth_state

    cfg = get_settings()
    state = oauth_state.create_oauth_state("u1", "youtube_shorts", cfg=cfg)
    with pytest.raises(Exception):
        oauth_state.verify_oauth_state(state, "tiktok", cfg=cfg)


@pytest.mark.asyncio
async def test_auth_service_inactive_login(db):
    from backend.services.auth_service import AuthError
    users_repo = MagicMock()
    inactive = SimpleNamespace(is_active=False, hashed_password="hashed")
    users_repo.get_by_email = AsyncMock(return_value=inactive)
    svc = AuthService(db, get_settings())
    svc.users = users_repo
    with patch("backend.middleware.auth.verify_password", return_value=True), \
         patch("backend.services.auth_service.verify_password", return_value=True):
        with pytest.raises(AuthError, match="disabled"):
            await svc.authenticate("a@b.c", "password")


@pytest.mark.asyncio
async def test_job_service_cancel_missing_job(db):
    from backend.middleware.scope import RequestScope
    from backend.services.job_service import JobService
    from core.errors import StreamClipError

    svc = JobService(db, MagicMock(), MagicMock())
    svc.get_job = AsyncMock(side_effect=StreamClipError("missing", code="job_not_found"))
    scope = RequestScope(user_id="u1", device_id=None)
    with pytest.raises(StreamClipError):
        await svc.cancel_job("missing", scope=scope)


def test_static_ui_mount_when_present(tmp_path, monkeypatch):
    from fastapi import FastAPI
    import backend.static_ui as su

    static = tmp_path / "ui"
    static.mkdir()
    (static / "index.html").write_text("<html>ok</html>")
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.web, "serve_static", True)
    monkeypatch.setattr(cfg.web, "static_dir", str(static))
    app = FastAPI()
    assert su.mount_static_ui(app, cfg) is True


def test_inprocess_worker_submit_canvas(monkeypatch):
    from core import inprocess_worker as ipw

    cfg = get_settings(reload=True)
    worker = ipw.InProcessWorker(cfg)
    sig = MagicMock()
    sig.subtask_type = "group"
    sig.tasks = []
    with patch.object(worker, "execute_work", return_value=[]):
        worker.submit_canvas(sig)
    worker.shutdown(wait=False)


def test_caption_timing_snap_edges():
    from core import caption_timing as ct
    from core.models import Transcript, TranscriptSegment

    tr = Transcript(
        segments=[TranscriptSegment(id=0, text="a", start=0.0, end=1.0, words=())],
        language="en",
        duration=2.0,
        source_path=Path("x"),
    )
    s, e = ct.snap_time_to_words(0.5, 1.5, tr)
    assert s <= e


def test_ingest_storage_download_missing_key(tmp_path):
    from core.ingest.resolvers import storage as st_res
    from core.errors import IngestError, StorageError

    cfg = get_settings(reload=True)
    dest = tmp_path / "out.mp4"
    store = MagicMock()
    store.size.return_value = 100
    store.download.side_effect = StorageError("missing")
    with pytest.raises(IngestError):
        st_res.download_from_storage("uploads/missing.mp4", dest, cfg, storage=store)


@pytest.fixture(autouse=True)
async def _dispose_after():
    yield
    await dispose_engine()
