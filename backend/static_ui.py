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
    Returns ``None`` when no shell matches (caller chooses a fallback).
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


def is_jobs_spa_path(normalized: str) -> bool:
    """True for ``jobs`` / ``jobs/...`` client routes (not ``/api/jobs``)."""
    return normalized == "jobs" or normalized.startswith("jobs/")


def resolve_jobs_miss(static_dir: Path) -> Path | None:
    """Fallback HTML when a ``/jobs/*`` path has no resolved shell.

    Prefer the dynamic job shell so create→``/jobs/<id>/`` still opens the
    live overview. Never return the site home index.
    """
    job_shell = static_dir / "jobs" / "_" / "index.html"
    if job_shell.is_file():
        return job_shell
    not_found = static_dir / "404.html"
    if not_found.is_file():
        return not_found
    return None


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
        # Exported route shell (literal path or dynamic ``_``). Unknown non-job
        # paths fall back to home; job misses never do (create→home bug).
        shell = resolve_spa_html(static_dir, normalized)
        if shell is not None:
            return FileResponse(shell, headers=_SPA_NO_CACHE)
        if is_jobs_spa_path(normalized):
            job_miss = resolve_jobs_miss(static_dir)
            if job_miss is not None:
                status = 404 if job_miss.name == "404.html" else 200
                return FileResponse(job_miss, status_code=status, headers=_SPA_NO_CACHE)
            raise HTTPException(status_code=404, detail="Job UI shell missing")
        return FileResponse(static_dir / "index.html", headers=_SPA_NO_CACHE)

    log.info("static_ui_mounted", dir=str(static_dir))
    return True
