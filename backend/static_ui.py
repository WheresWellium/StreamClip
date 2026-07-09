"""
Serve exported Next.js static UI from FastAPI (ADR-001 §4.7).

When ``web.static_dir`` exists, mount assets and SPA fallback at ``/``.
API routes (`/api/*`, `/storage/*`, `/docs`) remain on the sidecar.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import Settings

log = structlog.get_logger(__name__)

_SPA_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}

def _is_reserved_api_path(path: str) -> bool:
    return (
        path.startswith("api/")
        or path.startswith("storage/")
        or path == "openapi.json"
        or path.startswith("docs")
        or path.startswith("redoc")
        or path.startswith("metrics")
    )


def resolve_static_dir(cfg: Settings) -> Path | None:
    """Return static UI directory if enabled and present."""
    if not cfg.web.serve_static:
        return None
    path = Path(cfg.web.static_dir)
    if not path.is_absolute():
        from core.ffmpeg_bins import app_root

        path = (app_root() / path).resolve()
    if not path.is_dir():
        return None
    if not (path / "index.html").is_file():
        log.warning("static_ui_missing_index", dir=str(path))
        return None
    return path


def mount_static_ui(app: FastAPI, cfg: Settings) -> bool:
    """
    Mount exported Next.js output. Returns True when mounted.

    Call after all API routers are registered.
    """
    static_dir = resolve_static_dir(cfg)
    if static_dir is None:
        return False

    next_dir = static_dir / "_next"
    if next_dir.is_dir():
        app.mount("/_next", StaticFiles(directory=next_dir), name="next_static")

    @app.get("/", include_in_schema=False)
    async def static_index() -> FileResponse:
        return FileResponse(static_dir / "index.html", headers=_SPA_NO_CACHE)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def static_spa(full_path: str) -> FileResponse:
        normalized = full_path.lstrip("/")
        if _is_reserved_api_path(normalized):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = static_dir / normalized
        if candidate.is_file():
            # Hashed Next assets under _next/ are mounted separately; HTML shells
            # should not be cached so desktop installs pick up fresh UI after update.
            headers = _SPA_NO_CACHE if candidate.suffix == ".html" else None
            return FileResponse(candidate, headers=headers)
        # Next export may emit path/index.html
        index_nested = static_dir / normalized / "index.html"
        if index_nested.is_file():
            return FileResponse(index_nested, headers=_SPA_NO_CACHE)
        return FileResponse(static_dir / "index.html", headers=_SPA_NO_CACHE)

    log.info("static_ui_mounted", dir=str(static_dir))
    return True
