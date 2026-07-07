"""DB session helpers."""

from __future__ import annotations

import pytest

from backend.db.session import db_session, dispose_engine, get_sync_engine_url


@pytest.mark.asyncio
async def test_db_session_commits():
    await dispose_engine()
    async with db_session() as session:
        await session.execute(__import__("sqlalchemy").text("SELECT 1"))
    await dispose_engine()


def test_sync_engine_url():
    url = get_sync_engine_url()
    assert url.startswith("postgresql") or url.startswith("sqlite")
