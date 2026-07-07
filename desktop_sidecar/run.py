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

APP_DATA_DIR_NAME = "StreamClip"


def app_root() -> Path:
    """Repository root in dev; bundled resources dir when frozen.

    PyInstaller ≥6 one-dir places datas under ``_internal/`` next to the exe
    and exposes it as ``sys._MEIPASS`` — config/alembic/static live there,
    not beside the executable.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def desktop_data_dir() -> Path | None:
    """Per-user data dir for packaged installs (MASTER_TODO §4.18).

    Resolution order:
      1. ``STREAMCLIP_DESKTOP_DATA_DIR`` env override (any platform, incl. dev)
      2. When frozen (PyInstaller): ``%LOCALAPPDATA%\\StreamClip``,
         falling back to ``~/.streamclip`` where LOCALAPPDATA is unset
      3. Dev (not frozen, no override): ``None`` — config defaults apply
    """
    override = os.environ.get("STREAMCLIP_DESKTOP_DATA_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_DATA_DIR_NAME
        return Path.home() / ".streamclip"
    return None


def configure_data_dirs(data_dir: Path) -> None:
    """Point DB/storage/workspace/cache env overrides into *data_dir*.

    Uses ``setdefault`` so explicit user env vars always win; the config
    file keeps its dev-relative defaults.
    """
    workspace = data_dir / "workspace"
    storage = data_dir / "storage"
    cache = data_dir / "cache"
    for d in (data_dir, workspace, storage, cache):
        d.mkdir(parents=True, exist_ok=True)

    db_path = (data_dir / "streamclip.db").as_posix()
    os.environ.setdefault("STREAMCLIP_DATABASE__URL", f"sqlite+aiosqlite:///{db_path}")
    os.environ.setdefault("STREAMCLIP_DATABASE__SYNC_URL", f"sqlite:///{db_path}")
    os.environ.setdefault("STREAMCLIP_STORAGE__LOCAL_ROOT", str(storage))
    os.environ.setdefault("STREAMCLIP_WORKSPACE_DIR", str(workspace))
    os.environ.setdefault("STREAMCLIP_CACHE_DIR", str(cache))
    log.info("sidecar_data_dir", path=str(data_dir))


def configure_desktop_env(root: Path | None = None) -> Path:
    """Set env defaults for embedded desktop mode."""
    base = root or app_root()
    os.chdir(base)
    os.environ.setdefault("STREAMCLIP_APP_ROOT", str(base))
    config_path = base / "config" / "desktop.yaml"
    if config_path.is_file():
        os.environ.setdefault("STREAMCLIP_CONFIG", str(config_path))
    data_dir = desktop_data_dir()
    if data_dir is not None:
        configure_data_dirs(data_dir)
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


def start_model_prefetch() -> bool:
    """Warm ML models in the background so the first job doesn't stall (§4.8).

    Opt out with ``STREAMCLIP_SIDECAR_SKIP_PREFETCH=1``. Progress is exposed
    at ``/api/health/models``.
    """
    if os.environ.get("STREAMCLIP_SIDECAR_SKIP_PREFETCH", "").lower() in ("1", "true", "yes"):
        return False
    from core.config import get_settings
    from core.model_prefetch import start_prefetch

    return start_prefetch(get_settings())


def run_server(
    *,
    host: str | None = None,
    port: int | None = None,
    root: Path | None = None,
) -> None:
    """Start FastAPI + in-process worker (desktop profile)."""
    # Env overrides MUST land before backend.main import: modules resolve
    # get_settings() at import time and would cache the Postgres defaults.
    base = configure_desktop_env(root)

    import uvicorn

    from backend.main import create_app
    bind_host = host or os.environ.get("STREAMCLIP_SIDECAR_HOST", DEFAULT_HOST)
    bind_port = int(port or os.environ.get("STREAMCLIP_SIDECAR_PORT", DEFAULT_PORT))

    if os.environ.get("STREAMCLIP_SIDECAR_SKIP_MIGRATE", "").lower() not in ("1", "true", "yes"):
        run_migrations(base)

    start_model_prefetch()

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
