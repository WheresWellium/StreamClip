"""Phase 2b-ii coverage — job waveform endpoint + caption_words_per_group."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.jobs as jobs_api
import core.tasks.pipeline_tasks as pt
from backend.api.schemas import UpdateClipRequest
from backend.db.models import ClipStatus
from backend.db.session import get_db
from backend.middleware.scope import RequestScope, get_request_scope
from backend.services.job_service import JobService
from core.ingest.waveform import ensure_job_waveform, render_waveform_png, waveform_storage_key

SCOPE = RequestScope(user_id=None, device_id="waveformdev001")


@pytest.fixture
def jobs_client(app, client):
    session = MagicMock()
    session.commit = AsyncMock()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_request_scope] = lambda: SCOPE
    yield SimpleNamespace(client=client, session=session)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_request_scope, None)


# ─── core/ingest/waveform.py ─────────────────────────────────────────────────

def test_render_waveform_png_writes_file(tmp_path: Path):
    source = tmp_path / "tone.wav"
    source.write_bytes(b"not-real-audio")
    out = tmp_path / "waveform.png"

    with patch("core.ingest.waveform.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        result = render_waveform_png(source, out)

    assert result == out
    run.assert_called_once()


def test_waveform_storage_key_shape():
    assert waveform_storage_key("job-1").endswith("meta/waveform.png")
    assert "job-1" in waveform_storage_key("job-1")


def test_ensure_job_waveform_skips_when_cached(tmp_path):
    storage = MagicMock()
    storage.exists.return_value = True
    cfg = SimpleNamespace(workspace_dir=tmp_path)

    key = ensure_job_waveform("job-1", tmp_path / "source.mp4", cfg, storage)

    assert key == waveform_storage_key("job-1")
    storage.upload.assert_not_called()


def test_ensure_job_waveform_renders_and_uploads(tmp_path):
    storage = MagicMock()
    storage.exists.return_value = False
    cfg = SimpleNamespace(workspace_dir=tmp_path)

    def fake_render(source: Path, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"png")
        return output

    with patch("core.ingest.waveform.render_waveform_png", side_effect=fake_render):
        key = ensure_job_waveform("job-2", tmp_path / "source.mp4", cfg, storage)

    assert key == waveform_storage_key("job-2")
    storage.upload.assert_called_once()
    assert storage.upload.call_args.kwargs.get("content_type") == "image/png"


def test_ensure_job_waveform_failure_is_non_fatal(tmp_path):
    storage = MagicMock()
    storage.exists.return_value = False
    cfg = SimpleNamespace(workspace_dir=tmp_path)

    with patch(
        "core.ingest.waveform.render_waveform_png",
        side_effect=RuntimeError("no audio stream"),
    ):
        key = ensure_job_waveform("job-3", tmp_path / "source.mp4", cfg, storage)

    assert key is None
    storage.upload.assert_not_called()


# ─── GET /api/jobs/{id}/waveform ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_job_waveform_returns_presigned_url(jobs_client):
    svc = MagicMock()
    svc.get_job = AsyncMock()
    storage = MagicMock()
    storage.exists.return_value = True
    storage.presigned_get_url.return_value = "https://minio/waveform.png?sig=x"

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "make_storage", return_value=storage):
        resp = await jobs_client.client.get("/api/jobs/job-1/waveform")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"url": "https://minio/waveform.png?sig=x"}
    svc.get_job.assert_awaited()  # ownership check ran


@pytest.mark.asyncio
async def test_get_job_waveform_404_when_not_ready(jobs_client):
    svc = MagicMock()
    svc.get_job = AsyncMock()
    storage = MagicMock()
    storage.exists.return_value = False

    with patch.object(jobs_api, "_get_service", return_value=svc), \
         patch.object(jobs_api, "make_storage", return_value=storage):
        resp = await jobs_client.client.get("/api/jobs/job-1/waveform")

    assert resp.status_code == 404
    assert resp.json()["code"] == "waveform_not_ready"


# ─── caption_words_per_group — service merge ─────────────────────────────────

def _make_clip(**kw):
    defaults = dict(
        id="c1",
        job_id="job-1",
        start_secs=10.0,
        end_secs=40.0,
        status=ClipStatus.DONE,
        render_overrides={},
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_update_clip_persists_words_per_group():
    svc = JobService(MagicMock(), MagicMock(), MagicMock())
    clip = _make_clip()
    job = SimpleNamespace(id="job-1", clips=[clip])
    svc.get_job = AsyncMock(return_value=job)
    svc.clips = MagicMock()
    svc.clips.update_boundaries = AsyncMock()
    svc.clips.get = AsyncMock(return_value=clip)
    svc.db = MagicMock()
    svc.db.flush = AsyncMock()

    body = UpdateClipRequest(caption_words_per_group=2, rerender=False)
    await svc.update_clip("job-1", "c1", body, scope=SCOPE)

    overrides = svc.clips.update_boundaries.call_args.kwargs["render_overrides"]
    assert overrides["caption_words_per_group"] == 2


def test_update_clip_request_rejects_out_of_range():
    with pytest.raises(ValueError):
        UpdateClipRequest(caption_words_per_group=0)
    with pytest.raises(ValueError):
        UpdateClipRequest(caption_words_per_group=9)


# ─── caption_words_per_group — pipeline override ─────────────────────────────

@pytest.fixture
def restore_wpg():
    original = pt.cfg.caption.words_per_group
    yield
    pt.cfg.caption.words_per_group = original


def test_apply_clip_overrides_sets_words_per_group(restore_wpg):
    clip = SimpleNamespace(render_overrides={"caption_words_per_group": 2})
    pt._apply_clip_overrides(SimpleNamespace(), clip)
    assert pt.cfg.caption.words_per_group == 2


@pytest.mark.parametrize("bad", [0, 9, "3", None, 2.5])
def test_apply_clip_overrides_ignores_invalid_wpg(restore_wpg, bad):
    pt.cfg.caption.words_per_group = 4
    clip = SimpleNamespace(render_overrides={"caption_words_per_group": bad})
    pt._apply_clip_overrides(SimpleNamespace(), clip)
    assert pt.cfg.caption.words_per_group == 4


def test_apply_job_config_resets_words_per_group(restore_wpg):
    pt.cfg.caption.words_per_group = 2
    job = SimpleNamespace(config_snapshot={})
    pt._apply_job_config(job)
    assert pt.cfg.caption.words_per_group == pt._DEFAULT_WORDS_PER_GROUP
