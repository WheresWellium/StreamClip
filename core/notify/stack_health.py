"""Periodic stack probes for autonomous ops alerts (Phase 0+).

Runs on the Celery Beat schedule (and in-process beat on desktop). Posts
``stack_degraded`` to ``OPS_WEBHOOK_URL`` when DB/Redis/storage fail, with a
cooldown so a sustained outage does not flood the inbox.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from core.config import Settings, get_settings

log = structlog.get_logger(__name__)

# Avoid webhook storms while a dependency is down.
_COOLDOWN_SECS = 15 * 60
_last_alert_mono: float = 0.0
_last_status: str = "ok"


def probe_stack_dependencies(cfg: Settings | None = None) -> dict[str, Any]:
    """
    Sync probe of DB, Redis (when not inprocess), and object storage.

    Returns ``{"status": "ok"|"degraded", "checks": {...}, "failures": [...]}``.
    """
    settings = cfg or get_settings()
    checks: dict[str, bool] = {}
    failures: list[str] = []

    # Database (sync URL — Beat has no async loop requirement)
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database.sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
        engine.dispose()
    except Exception as exc:
        checks["database"] = False
        failures.append(f"database: {exc}")
        log.warning("stack_probe_db_fail", error=str(exc))

    # Redis — not required in desktop inprocess mode
    if settings.queue.backend == "inprocess":
        checks["redis"] = True
    else:
        try:
            import redis

            client = redis.from_url(settings.redis.url, socket_connect_timeout=3)
            client.ping()
            client.close()
            checks["redis"] = True
        except Exception as exc:
            checks["redis"] = False
            failures.append(f"redis: {exc}")
            log.warning("stack_probe_redis_fail", error=str(exc))

    # Object storage
    try:
        from core.storage import make_storage

        make_storage(settings).list_prefix("__health__/")
        checks["storage"] = True
    except Exception as exc:
        checks["storage"] = False
        failures.append(f"storage: {exc}")
        log.warning("stack_probe_storage_fail", error=str(exc))

    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks, "failures": failures}


def should_emit_stack_alert(status: str, *, now: float | None = None) -> bool:
    """True when we should POST a webhook for this probe result."""
    global _last_alert_mono, _last_status
    mono = time.monotonic() if now is None else now
    if status == "ok":
        _last_status = "ok"
        return False
    if _last_status == "ok" or (mono - _last_alert_mono) >= _COOLDOWN_SECS:
        _last_alert_mono = mono
        _last_status = status
        return True
    return False


def reset_stack_alert_state() -> None:
    """Test helper — clear cooldown / last status."""
    global _last_alert_mono, _last_status
    _last_alert_mono = 0.0
    _last_status = "ok"
