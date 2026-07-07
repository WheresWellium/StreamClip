"""SQLite desktop database profile (ADR-001 §4.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from backend.db.models import JobStatus
from backend.db.repositories import JobRepository
from backend.db.session import db_session, dispose_engine, get_sync_engine_url
from core.config import get_settings


def _sqlite_urls(db_path: Path) -> tuple[str, str]:
    resolved = db_path.resolve().as_posix()
    return (
        f"sqlite+aiosqlite:///{resolved}",
        f"sqlite:///{resolved}",
    )


@pytest.fixture
def sqlite_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point settings at a temp SQLite file and reload cached singletons."""
    db_path = tmp_path / "streamclip_test.db"
    async_url, sync_url = _sqlite_urls(db_path)
    monkeypatch.setenv("STREAMCLIP_DATABASE__URL", async_url)
    monkeypatch.setenv("STREAMCLIP_DATABASE__SYNC_URL", sync_url)
    monkeypatch.delenv("STREAMCLIP_CONFIG", raising=False)
    get_settings(reload=True)
    yield db_path
    get_settings(reload=True)


def test_database_config_is_sqlite(sqlite_settings: Path) -> None:
    cfg = get_settings()
    assert cfg.database.is_sqlite is True
    assert cfg.database.url.startswith("sqlite+aiosqlite:")
    assert cfg.database.sync_url.startswith("sqlite:")


def test_sync_engine_url_uses_sqlite(sqlite_settings: Path) -> None:
    assert get_sync_engine_url().startswith("sqlite:")


def test_alembic_upgrade_head(sqlite_settings: Path) -> None:
    sync_url = get_sync_engine_url()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")
    assert sqlite_settings.exists()


@pytest.mark.asyncio
async def test_job_repository_crud(sqlite_settings: Path) -> None:
    sync_url = get_sync_engine_url()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")

    await dispose_engine()
    try:
        async with db_session() as session:
            repo = JobRepository(session)
            job = await repo.create(
                status=JobStatus.QUEUED,
                config_snapshot={"profile": "sqlite"},
            )
            assert job.id

            loaded = await repo.get(job.id)
            assert loaded is not None
            assert loaded.status == JobStatus.QUEUED
            assert loaded.config_snapshot == {"profile": "sqlite"}
    finally:
        await dispose_engine()
