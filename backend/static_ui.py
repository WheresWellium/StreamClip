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


def resolve_spa_html(static_dir: Path, normalized: str) -> Path | None:
    """Resolve an exported HTML shell for a client-side route.

    Next.js static export writes dynamic segments (``/jobs/[id]``) to a literal
    ``_`` directory (``jobs/_/index.html``). Walk the export tree preferring the
    literal segment, then the ``_`` dynamic shell, so real ids like
    ``/jobs/<uuid>/`` open the correct page instead of falling back to home.
    Returns ``None`` when no shell matches (caller serves the root index).
    """
    segments = [seg for seg in normalized.split("/") if seg]
    cursor = static_dir
    for segment in segments:
        literal = cursor / segment
        if literal.is_dir():
            cursor = literal
            continue
        dynamic = cursor / "_"
        if dynamic.is_dir():
            cursor = dynamic
            continue
        return None
    index_html = cursor / "index.html"
    return index_html if index_html.is_file() else None


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
        # Exported route shell (literal ``path/index.html`` or dynamic ``_`` shell
        # for routes like ``/jobs/<id>/``). Falls back to the root index for
        # genuinely unknown paths so the SPA can render its own not-found.
        shell = resolve_spa_html(static_dir, normalized)
        if shell is not None:
            return FileResponse(shell, headers=_SPA_NO_CACHE)
        return FileResponse(static_dir / "index.html", headers=_SPA_NO_CACHE)

    log.info("static_ui_mounted", dir=str(static_dir))
    return True
