"""
StreamClip — Database Session Management

Async SQLAlchemy 2.0 engine with proper connection pooling and a
FastAPI-compatible dependency that yields one session per request.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import Settings, get_settings

log = structlog.get_logger(__name__)


# ─── Engine + session factory ────────────────────────────────────────────────

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine(cfg: Settings | None = None) -> AsyncEngine:
    global _engine
    if _engine is None:
        cfg = cfg or get_settings()
        _engine = create_async_engine(
            cfg.database.url,
            echo=cfg.database.echo,
            pool_size=cfg.database.pool_size,
            max_overflow=cfg.database.max_overflow,
            pool_pre_ping=cfg.database.pool_pre_ping,
            future=True,
        )
        log.info("db_engine_created", url=cfg.database.url.split("@")[-1])
    return _engine


def get_sessionmaker(cfg: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_engine(cfg)
        _sessionmaker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


# ─── FastAPI dependency ──────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a session per request. Commits on success, rolls back on exception.
    Use as a FastAPI dependency: `Depends(get_db)`.
    """
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Context manager (for Celery tasks, scripts) ────────────────────────────

@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """For use outside FastAPI request scope (Celery tasks, CLI scripts)."""
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Sync engine (for Alembic migrations) ───────────────────────────────────

def get_sync_engine_url() -> str:
    """Alembic uses sync drivers — return the psycopg URL."""
    cfg = get_settings()
    return cfg.database.sync_url
