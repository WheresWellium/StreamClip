"""
StreamClip — Database Session Management

Async SQLAlchemy 2.0 engine with proper connection pooling and a
FastAPI-compatible dependency that yields one session per request.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from core.config import Settings, get_settings

log = structlog.get_logger(__name__)


# ─── Engine + session factory ────────────────────────────────────────────────

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _sqlite_engine_kwargs(db_url: str, *, echo: bool) -> dict:
    return {
        "url": db_url,
        "echo": echo,
        "poolclass": NullPool,
        "connect_args": {"check_same_thread": False},
        "future": True,
    }


def get_engine(cfg: Settings | None = None) -> AsyncEngine:
    global _engine
    if _engine is None:
        cfg = cfg or get_settings()
        db = cfg.database
        if db.is_sqlite:
            _engine = create_async_engine(**_sqlite_engine_kwargs(db.url, echo=db.echo))
            # SQLite does not enforce FK constraints unless pragma is enabled.
            @event.listens_for(_engine.sync_engine, "connect")
            def _sqlite_pragma(dbapi_conn, _connection_record) -> None:  # noqa: N803
                # busy_timeout: desktop in-process workers race support inserts
                # with webhook/email tasks on the same SQLite file.
                # WAL only for on-disk DBs — :memory: / shared-cache test URLs
                # break under NullPool if WAL is forced.
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                url_l = db.url.lower()
                if ":memory:" not in url_l and "mode=memory" not in url_l:
                    cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        else:
            _engine = create_async_engine(
                db.url,
                echo=db.echo,
                pool_size=db.pool_size,
                max_overflow=db.max_overflow,
                pool_pre_ping=db.pool_pre_ping,
                future=True,
            )
        log.info(
            "db_engine_created",
            dialect="sqlite" if db.is_sqlite else "postgresql",
            url=db.url.split("@")[-1],
        )
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
    """Alembic uses sync drivers — return the configured sync URL."""
    cfg = get_settings()
    return cfg.database.sync_url


async def dispose_engine() -> None:
    """Close pooled connections — use in tests and graceful shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
