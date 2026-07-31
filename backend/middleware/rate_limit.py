"""
StreamClip — Rate Limiting

Sliding-window token bucket implemented as a Redis sorted set. Tracks
two limits per identity:
  • requests_per_minute — general API rate
  • jobs_per_hour       — expensive: pipeline creation

Identity is the user_id when authenticated, IP address otherwise.
"""

from __future__ import annotations

import time
from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, Request, status

from backend.middleware.auth import get_current_user_id
from core.config import Settings, get_settings

log = structlog.get_logger(__name__)


_redis: aioredis.Redis | None = None


async def _get_redis(cfg: Settings) -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(cfg.redis.url, decode_responses=True)
    return _redis


# ─── Sliding-window counter ──────────────────────────────────────────────────

async def _check_window(
    redis: aioredis.Redis,
    key: str,
    *,
    window_secs: int,
    limit: int,
) -> tuple[bool, int]:
    """
    Returns (allowed, remaining). Uses a sorted set where members are
    request timestamps. Old entries are pruned each call.
    """
    now = time.time()
    cutoff = now - window_secs

    # Pipeline all four operations atomically
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, cutoff)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_secs + 1)
    _, current_count, _, _ = await pipe.execute()

    remaining = max(0, limit - current_count - 1)
    return (current_count < limit, remaining)


# ─── FastAPI dependencies ────────────────────────────────────────────────────

async def rate_limit_request(
    request: Request,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
) -> None:
    """General API rate limit (per minute)."""
    cfg = get_settings()
    if not cfg.rate_limit.enabled:
        return

    identity = user_id or request.client.host if request.client else "unknown"
    key = f"ratelimit:req:{identity}"

    redis = await _get_redis(cfg)
    allowed, remaining = await _check_window(
        redis, key,
        window_secs=60, limit=cfg.rate_limit.requests_per_minute,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
        )

    # Inject remaining for response headers (set via middleware later if desired)
    request.state.ratelimit_remaining = remaining


async def rate_limit_auth(request: Request) -> None:
    """Tighter, IP-scoped limit for unauthenticated auth endpoints.

    Login / register / forgot-password are the brute-force and email-bombing
    surface, so they get a dedicated, lower ceiling than the general API limit.
    Keyed by client IP because there is no authenticated user yet.
    """
    cfg = get_settings()
    if not cfg.rate_limit.enabled:
        return

    identity = request.client.host if request.client else "unknown"
    key = f"ratelimit:auth:{identity}"

    redis = await _get_redis(cfg)
    allowed, _ = await _check_window(
        redis, key,
        window_secs=60, limit=cfg.rate_limit.auth_per_minute,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Wait a minute and try again.",
            headers={"Retry-After": "60"},
        )


async def rate_limit_job_creation(
    request: Request,
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
) -> None:
    """Specific limit on expensive job creation (per hour)."""
    cfg = get_settings()
    if not cfg.rate_limit.enabled:
        return

    identity = user_id or request.client.host if request.client else "unknown"
    key = f"ratelimit:jobs:{identity}"

    redis = await _get_redis(cfg)
    allowed, _ = await _check_window(
        redis, key,
        window_secs=3600, limit=cfg.rate_limit.jobs_per_hour,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Job creation limit ({cfg.rate_limit.jobs_per_hour}/hour) exceeded",
            headers={"Retry-After": "3600"},
        )
