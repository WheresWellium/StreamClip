"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.session import dispose_engine
from backend.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    await dispose_engine()
    transport = ASGITransport(app=app)
    # Real web clients always send a device id; anonymous scope requires it
    headers = {"X-Device-Id": "test-device-0001"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    await dispose_engine()


@pytest.fixture
async def db():
    await dispose_engine()
    from backend.db.session import get_sessionmaker

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await dispose_engine()
