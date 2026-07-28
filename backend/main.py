"""
StreamClip — FastAPI Application Entry Point

Wires together every router, middleware, and lifecycle hook.
Production-ready:
  • Structured JSON logging
  • Sentry + OpenTelemetry hooks (no-op until DSN/endpoint configured)
  • Graceful startup / shutdown of DB and Redis pools
  • Global exception handler that maps StreamClipError → HTTP response
  • OpenAPI docs at /docs, ReDoc at /redoc
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.api import admin, assets, auth, commerce, devices, distribution, health, jobs, license, local_storage, metrics, settings, support, templates, title_suggestions, uploads, vault
from backend.observability import init_opentelemetry
from core.config import get_settings
from core.errors import StreamClipError, sanitize_user_message
from core.logging_redact import redact_log_event


# ─── Structured logging ──────────────────────────────────────────────────────

def _configure_logging() -> None:
    cfg = get_settings()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level),
        format="%(message)s",
    )
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        redact_log_event,
    ]
    if cfg.log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, cfg.log_level)
        ),
    )


_configure_logging()
log = structlog.get_logger(__name__)


# ─── Optional: Sentry ────────────────────────────────────────────────────────

def _init_sentry() -> None:
    cfg = get_settings()
    if not cfg.observability.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=cfg.observability.sentry_dsn,
            environment=cfg.environment,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
        )
        log.info("sentry_initialised")
    except ImportError:
        log.warning("sentry_sdk_not_installed")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    log.info(
        "app_startup",
        environment=cfg.environment,
        version="1.0.0",
        log_level=cfg.log_level,
    )

    # Loudly warn when the default JWT secret is still set outside dev.
    # This does not raise — it would break existing dev workflows.
    # In production, generate a strong key: openssl rand -hex 32
    if cfg.auth.secret_key == "CHANGE_ME_IN_PRODUCTION" and cfg.environment != "development":
        log.critical(
            "SECURITY_WARNING",
            message=(
                "Default JWT secret key 'CHANGE_ME_IN_PRODUCTION' is still in use. "
                "Set STREAMCLIP_AUTH__SECRET_KEY to a strong random value: "
                "openssl rand -hex 32"
            ),
        )

    _init_sentry()
    init_opentelemetry(cfg)

    # Warm DB connection pool
    from backend.db.session import get_engine
    engine = get_engine(cfg)
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("db_pool_warm")
    except Exception as exc:
        log.warning("db_warm_failed", error=str(exc))

    if cfg.queue.backend == "inprocess":
        from core.inprocess_worker import start_inprocess_worker

        start_inprocess_worker(cfg)
        log.info("inprocess_worker_ready")

    yield

    if cfg.queue.backend == "inprocess":
        from core.inprocess_worker import stop_inprocess_worker

        stop_inprocess_worker()

    log.info("app_shutdown")
    await engine.dispose()


# ─── App factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    cfg = get_settings()

    # Desktop sidecar keeps OpenAPI enabled for Settings → API (local-only).
    api_docs = cfg.environment != "production" or cfg.queue.backend == "inprocess"

    app = FastAPI(
        title="qClip API",
        description="AI-powered clip pipeline",
        version="1.0.0",
        docs_url="/docs" if api_docs else None,
        redoc_url="/redoc" if api_docs else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors.allow_origins,
        allow_methods=cfg.cors.allow_methods,
        allow_headers=cfg.cors.allow_headers,
        allow_credentials=cfg.cors.allow_credentials,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # ── Request timing middleware ─────────────────────────────────────────
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next) -> Any:
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - t0
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        if cfg.observability.enable_metrics and request.url.path != "/metrics":
            metrics.REQUEST_DURATION.labels(
                method=request.method,
                path=request.url.path,
            ).observe(elapsed)
            metrics.REQUESTS_TOTAL.labels(
                method=request.method,
                path=request.url.path,
                status=str(response.status_code),
            ).inc()
        return response

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(jobs.router)
    app.include_router(title_suggestions.router)
    app.include_router(uploads.router)
    app.include_router(local_storage.router)
    app.include_router(templates.router)
    app.include_router(assets.router)
    app.include_router(settings.router)
    app.include_router(license.router)
    app.include_router(commerce.router)
    app.include_router(distribution.router)
    app.include_router(vault.router)
    app.include_router(devices.router)
    app.include_router(support.router)
    app.include_router(admin.router)
    if cfg.observability.enable_metrics:
        app.include_router(metrics.router)

    from backend.static_ui import mount_static_ui

    mount_static_ui(app, cfg)

    # ── Exception handlers ────────────────────────────────────────────────
    @app.exception_handler(StreamClipError)
    async def streamclip_error_handler(request: Request, exc: StreamClipError):
        log.warning(
            "domain_error",
            code=exc.code,
            message=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"code": "validation_error", "errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            message = sanitize_user_message(
                detail,
                fallback="Request could not be completed.",
            )
        elif isinstance(detail, list):
            message = "Validation failed."
        else:
            message = "Request could not be completed."
        log.warning(
            "http_exception",
            status=exc.status_code,
            path=request.url.path,
            detail_type=type(detail).__name__,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": f"http_{exc.status_code}", "message": message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.exception(
            "unhandled_exception",
            path=request.url.path,
            error_type=type(exc).__name__,
        )
        message = (
            str(exc)
            if cfg.environment == "development"
            else "An unexpected error occurred. Try again or report a bug."
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "internal_error", "message": message},
        )

    return app


app = create_app()


# ─── Dev server entrypoint ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
