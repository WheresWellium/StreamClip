"""
StreamClip — Health & Meta Endpoints

Two endpoints:
  GET /api/health  — Deep health check (DB, Redis, storage)
  GET /api/meta    — Public metadata: version, available presets, etc.
"""

from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import HealthResponse
from backend.db.session import get_db
from core.config import get_settings
from core.storage import make_storage

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["meta"])

VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HealthResponse:
    cfg = get_settings()

    # DB
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        log.warning("health_db_fail", error=str(exc))

    # Redis
    redis_ok = False
    try:
        r = aioredis.from_url(cfg.redis.url)
        await r.ping()
        await r.close()
        redis_ok = True
    except Exception as exc:
        log.warning("health_redis_fail", error=str(exc))

    # Storage
    storage_ok = False
    try:
        storage = make_storage(cfg)
        # List with an empty prefix is a cheap probe
        storage.list_prefix("__health__/")
        storage_ok = True
    except Exception as exc:
        log.warning("health_storage_fail", error=str(exc))

    ollama_ok: bool | None = None
    if cfg.llm.provider == "ollama":
        try:
            import httpx
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{cfg.llm.base_url.rstrip('/')}/api/tags")
            ollama_ok = resp.is_success
        except Exception as exc:
            log.warning("health_ollama_fail", error=str(exc))
            ollama_ok = False

    checks = [db_ok, redis_ok, storage_ok]
    if ollama_ok is not None:
        checks.append(ollama_ok)

    return HealthResponse(
        status="ok" if all(checks) else "degraded",
        version=VERSION,
        environment=cfg.environment,
        redis=redis_ok,
        database=db_ok,
        storage=storage_ok,
        ollama=ollama_ok,
    )


@router.get("/meta")
async def meta() -> dict:
    """Public configuration that the frontend may use to populate selects."""
    from core.content_profiles import list_profiles

    return {
        "version": VERSION,
        "content_profiles": list_profiles(),
        "caption_styles": [
            "gaming_impact", "tiktok_pop", "minimal_white", "podcast_clean",
        ],
        "reframe_presets": [
            "fps_game", "moba", "battle_royale", "irl", "podcast", "auto",
        ],
        "emotion_labels": [
            "hype", "rage", "funny", "clutch", "fail", "weird", "neutral",
        ],
    }
