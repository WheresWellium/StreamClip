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

from backend.api.schemas import HealthResponse, StackHealthResponse
from backend.db.session import get_db
from core.config import get_settings
from core.model_prefetch import snapshot as model_prefetch_snapshot
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


@router.get("/health/models")
async def health_models() -> dict[str, object]:
    """First-run model prefetch progress (desktop profile; MASTER_TODO §4.8).

    Empty ``models`` means no prefetch was started (Docker path warms models
    in the image build instead).
    """
    models = model_prefetch_snapshot()
    ready = all(s["state"] in ("ready", "skipped") for s in models.values()) if models else True
    return {"ready": ready, "models": models}


@router.get("/health/stack", response_model=StackHealthResponse)
async def health_stack(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StackHealthResponse:
    """Extended stack health for onboarding wizard."""
    base = await health(db)
    cfg = get_settings()

    worker_ok: bool | None = None
    try:
        import httpx
        with httpx.Client(timeout=2.0) as client:
            resp = client.get("http://flower:5555/api/workers")
        worker_ok = resp.is_success
    except Exception:
        worker_ok = False

    checks = {
        "database": base.database,
        "redis": base.redis,
        "storage": base.storage,
    }
    if base.ollama is not None:
        checks["ollama"] = base.ollama

    return StackHealthResponse(
        status=base.status,
        version=VERSION,
        environment=cfg.environment,
        checks=checks,
        worker=worker_ok,
        beat=None,
        web=None,
    )


@router.get("/meta")
async def meta() -> dict:
    """Public configuration that the frontend may use to populate selects."""
    from core.creator_options import (
        list_aspect_ratios,
        list_caption_styles,
        list_content_profiles,
        list_reframe_presets,
    )
    from core.eta import processing_profile

    cfg = get_settings()

    return {
        "version": VERSION,
        "processing_profile": processing_profile(cfg),
        "content_profiles": list_content_profiles(),
        "caption_styles": list_caption_styles(),
        "reframe_presets": list_reframe_presets(),
        "aspect_ratios": list_aspect_ratios(),
        "emotion_labels": [
            "hype", "rage", "funny", "clutch", "fail", "weird", "neutral",
        ],
        "onboarding_sample_url": cfg.onboarding.sample_url,
        "features": {
            "audio_ingest": cfg.features.audio_ingest,
        },
    }
