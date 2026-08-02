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
from core.model_prefetch import has_failures as model_prefetch_has_failures
from core.model_prefetch import retry_prefetch as model_prefetch_retry
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

    # Redis — skipped in desktop/inprocess mode (no broker; not a failure)
    redis_ok = False
    inprocess_mode = cfg.queue.backend == "inprocess"
    if inprocess_mode:
        redis_ok = True  # Not applicable; treat as healthy so status isn't degraded
    else:
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

    # Keep this probe short and async — desktop boot polls /api/health every
    # few hundred ms; a sync 3s Ollama timeout was blocking the event loop and
    # making the ready-gate feel hung when Ollama isn't running yet.
    ollama_ok: bool | None = None
    if cfg.llm.provider == "ollama":
        try:
            import httpx

            async with httpx.AsyncClient(timeout=0.5) as client:
                resp = await client.get(f"{cfg.llm.base_url.rstrip('/')}/api/tags")
            ollama_ok = resp.is_success
        except Exception as exc:
            log.warning("health_ollama_fail", error=str(exc))
            ollama_ok = False

    checks = [db_ok, redis_ok, storage_ok]
    # Desktop/inprocess: report Ollama but don't mark the sidecar degraded —
    # models may still be downloading on first run.
    if ollama_ok is not None and not inprocess_mode:
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
    if not models:
        ready = True
    else:
        terminal = ("ready", "skipped", "failed")
        ready = all(s["state"] in terminal for s in models.values())
    failed = model_prefetch_has_failures()
    # Surface the first actionable hint so the UI never shows a dead spinner (F6).
    hint = ""
    if failed:
        for status in models.values():
            if status["state"] == "failed" and status.get("detail"):
                hint = status["detail"]
                break
    return {"ready": ready, "failed": failed, "hint": hint, "models": models}


@router.post("/health/models/retry")
async def health_models_retry() -> dict[str, object]:
    """Retry first-run model prefetch after a failure (F6).

    Resets non-ready models to pending and restarts the background thread.
    Returns ``started: false`` when a prefetch is already running.
    """
    started = model_prefetch_retry(get_settings())
    return {"started": started, "models": model_prefetch_snapshot()}


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

    try:
        from core.gpu_profile import cuda_available, is_darwin, mps_available, nvenc_available

        if is_darwin():
            checks["mps"] = mps_available()
            checks["cuda"] = False
            checks["nvenc"] = False
        else:
            checks["cuda"] = cuda_available()
            checks["nvenc"] = nvenc_available(cfg)
            checks["mps"] = False
    except Exception:
        checks["cuda"] = False
        checks["nvenc"] = False
        checks["mps"] = False

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
