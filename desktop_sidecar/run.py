"""
Desktop sidecar bootstrap (ADR-001 §4.6).

    python -m desktop_sidecar
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def app_root() -> Path:
    """Repository root in dev; install dir when frozen (PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def configure_desktop_env(root: Path | None = None) -> Path:
    """Set env defaults for embedded desktop mode."""
    base = root or app_root()
    os.chdir(base)
    os.environ.setdefault("STREAMCLIP_APP_ROOT", str(base))
    config_path = base / "config" / "desktop.yaml"
    if config_path.is_file():
        os.environ.setdefault("STREAMCLIP_CONFIG", str(config_path))
    return base


def run_migrations(root: Path | None = None) -> None:
    """Apply Alembic migrations (SQLite desktop DB)."""
    base = root or app_root()
    ini_path = base / "alembic.ini"
    if not ini_path.is_file():
        log.warning("sidecar_alembic_ini_missing", path=str(ini_path))
        return
    try:
        from alembic import command
        from alembic.config import Config

        from backend.db.session import get_sync_engine_url

        cfg = Config(str(ini_path))
        cfg.set_main_option("script_location", str(base / "alembic"))
        cfg.set_main_option("sqlalchemy.url", get_sync_engine_url())
        command.upgrade(cfg, "head")
        log.info("sidecar_migrations_applied")
    except Exception as exc:
        log.error("sidecar_migrations_failed", error=str(exc))
        raise


def run_server(
    *,
    host: str | None = None,
    port: int | None = None,
    root: Path | None = None,
) -> None:
    """Start FastAPI + in-process worker (desktop profile)."""
    import uvicorn

    from backend.main import create_app

    base = configure_desktop_env(root)
    bind_host = host or os.environ.get("STREAMCLIP_SIDECAR_HOST", DEFAULT_HOST)
    bind_port = int(port or os.environ.get("STREAMCLIP_SIDECAR_PORT", DEFAULT_PORT))

    if os.environ.get("STREAMCLIP_SIDECAR_SKIP_MIGRATE", "").lower() not in ("1", "true", "yes"):
        run_migrations(base)

    log.info("sidecar_starting", host=bind_host, port=bind_port, root=str(base))
    uvicorn.run(
        create_app(),
        host=bind_host,
        port=bind_port,
        workers=1,
        log_level=os.environ.get("STREAMCLIP_LOG_LEVEL", "info").lower(),
    )


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
