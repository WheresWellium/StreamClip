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

APP_DATA_DIR_NAME = "qClip"
LEGACY_APP_DATA_DIR_NAME = "StreamClip"

# Packaged / desktop data-dir installs: keep enough history for beta support
# without unbounded disk growth (~20 MiB sidecar + backups).
_SIDECAR_LOG_MAX_BYTES = 5 * 1024 * 1024
_SIDECAR_LOG_BACKUP_COUNT = 3


class _TeeIO:
    """Duplicate writes to the original stream and a size-rotating log file."""

    def __init__(
        self,
        primary,
        path: Path,
        *,
        max_bytes: int = _SIDECAR_LOG_MAX_BYTES,
        backup_count: int = _SIDECAR_LOG_BACKUP_COUNT,
    ) -> None:
        self._primary = primary
        self._path = path
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self._path.open("a", encoding="utf-8")

    def write(self, data: str) -> int:
        if not data:
            return 0
        try:
            self._primary.write(data)
        except Exception:  # noqa: BLE001 — never break logging on console failure
            pass
        try:
            self._maybe_rotate()
            self._fh.write(data)
            self._fh.flush()
        except Exception:  # noqa: BLE001
            pass
        return len(data)

    def _maybe_rotate(self) -> None:
        try:
            if self._fh.tell() < self._max_bytes:
                return
        except Exception:  # noqa: BLE001
            return
        self._fh.close()
        for idx in range(self._backup_count, 0, -1):
            src = self._path if idx == 1 else Path(f"{self._path}.{idx - 1}")
            dest = Path(f"{self._path}.{idx}")
            if src.is_file():
                if dest.is_file():
                    dest.unlink()
                src.rename(dest)
        self._fh = self._path.open("a", encoding="utf-8")

    def flush(self) -> None:
        try:
            self._primary.flush()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._fh.flush()
        except Exception:  # noqa: BLE001
            pass

    def isatty(self) -> bool:
        return bool(getattr(self._primary, "isatty", lambda: False)())

    @property
    def encoding(self) -> str:
        return getattr(self._primary, "encoding", "utf-8") or "utf-8"


def configure_sidecar_file_logging(
    data_dir: Path,
    *,
    max_bytes: int = _SIDECAR_LOG_MAX_BYTES,
    backup_count: int = _SIDECAR_LOG_BACKUP_COUNT,
) -> Path:
    """Tee stdout/stderr into ``data_dir/logs/sidecar.log`` (JSON-friendly).

    Structlog PrintLogger writes to stdout, so a FileHandler alone would miss
    the hot path. Call before importing ``backend.main``.
    """
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "sidecar.log"
    os.environ.setdefault("STREAMCLIP_LOG_JSON", "true")
    sys.stdout = _TeeIO(sys.stdout, log_path, max_bytes=max_bytes, backup_count=backup_count)
    sys.stderr = _TeeIO(sys.stderr, log_path, max_bytes=max_bytes, backup_count=backup_count)
    log.info("sidecar_log_file", path=str(log_path))
    return log_path


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


def _platform_app_data_candidates() -> list[Path]:
    """Preferred qClip dir first, then legacy StreamClip for existing installs."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
        return [base / APP_DATA_DIR_NAME, base / LEGACY_APP_DATA_DIR_NAME]
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
            return [base / APP_DATA_DIR_NAME, base / LEGACY_APP_DATA_DIR_NAME]
    return [Path.home() / ".qclip", Path.home() / ".streamclip"]


def desktop_data_dir() -> Path | None:
    """Per-user data dir for packaged installs (MASTER_TODO §4.18 / §5.4).

    Resolution order:
      1. ``STREAMCLIP_DESKTOP_DATA_DIR`` env override (any platform, incl. dev)
      2. When frozen (PyInstaller):
         - Prefer ``qClip`` app-data folder
         - Reuse legacy ``StreamClip`` folder if it already exists
         - else / missing LOCALAPPDATA: ``~/.qclip`` (legacy ``~/.streamclip``)
      3. Dev (not frozen, no override): ``None`` — config defaults apply
    """
    override = os.environ.get("STREAMCLIP_DESKTOP_DATA_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        candidates = _platform_app_data_candidates()
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]
    return None


def configure_data_dirs(data_dir: Path) -> None:
    """Point DB/storage/workspace/cache env overrides into *data_dir*.

    Uses ``setdefault`` so explicit user env vars always win; the config
    file keeps its dev-relative defaults.
    """
    workspace = data_dir / "workspace"
    storage = data_dir / "storage"
    cache = data_dir / "cache"
    logs = data_dir / "logs"
    for d in (data_dir, workspace, storage, cache, logs):
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
    from core.gpu_profile import apply_gpu_env_defaults

    apply_gpu_env_defaults()
    base = root or app_root()
    os.chdir(base)
    os.environ.setdefault("STREAMCLIP_APP_ROOT", str(base))
    config_path = base / "config" / "desktop.yaml"
    if config_path.is_file():
        os.environ.setdefault("STREAMCLIP_CONFIG", str(config_path))
    data_dir = desktop_data_dir()
    if data_dir is not None:
        configure_data_dirs(data_dir)
        # Tee before backend.main import so structlog PrintLogger is captured.
        configure_sidecar_file_logging(data_dir)
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
