"""Celery vault copy task coverage."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tasks import vault_tasks as vt


def _asyncio_run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(vt, "db_session", return_value=cm):
        yield session


@pytest.fixture(autouse=True)
def patch_safe_async():
    with patch.object(vt, "_safe_async", side_effect=_asyncio_run):
        yield


def _vault_row(**overrides):
    base = dict(
        id="vc-1",
        user_id="user-1",
        status="copying",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_copy_clip_to_vault_success(mock_db_cm, tmp_path):
    row = _vault_row()
    mock_db_cm.get = AsyncMock(return_value=row)

    storage = MagicMock()
    storage.exists.return_value = True

    def _download(key: str, dest: Path, on_progress=None) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"video")

    storage.download.side_effect = _download

    repo = MagicMock()
    repo.update_status = AsyncMock()

    with patch.object(vt, "make_storage", return_value=storage), \
         patch.object(vt, "VaultClipRepository", return_value=repo):
        out = vt.copy_clip_to_vault.run("vc-1", "clips/final.mp4", "clips/thumb.jpg")

    assert out["status"] == "ready"
    assert out["vault_clip_id"] == "vc-1"
    repo.update_status.assert_awaited_once()
    assert repo.update_status.await_args.kwargs["status"] == "ready"


def test_copy_clip_to_vault_missing_row(mock_db_cm):
    mock_db_cm.get = AsyncMock(return_value=None)
    with patch.object(vt, "make_storage", return_value=MagicMock()):
        out = vt.copy_clip_to_vault.run("ghost", "k", None)
    assert out["status"] == "error"


def test_copy_clip_to_vault_failure_marks_failed(mock_db_cm):
    row = _vault_row()
    mock_db_cm.get = AsyncMock(return_value=row)

    storage = MagicMock()
    storage.download.side_effect = OSError("disk full")

    repo = MagicMock()
    repo.update_status = AsyncMock()

    with patch.object(vt, "make_storage", return_value=storage), \
         patch.object(vt, "VaultClipRepository", return_value=repo):
        out = vt.copy_clip_to_vault.run("vc-1", "clips/final.mp4", None)

    assert out["status"] == "failed"
    repo.update_status.assert_awaited()
    assert repo.update_status.await_args.kwargs["status"] == "failed"
