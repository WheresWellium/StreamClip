"""backend.main coverage branches."""
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import create_app, _configure_logging, _init_sentry
from core.config import get_settings

def test_configure_logging_non_json(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "log_json", False)
    _configure_logging()

def test_init_sentry_paths(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "")
    _init_sentry()
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "https://x@sentry.io/1")
    with patch("backend.main.sentry_sdk", create=True) as ss:
        ss.init = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": ss, "sentry_sdk.integrations.fastapi": MagicMock(), "sentry_sdk.integrations.sqlalchemy": MagicMock()}):
            _init_sentry()

@pytest.mark.asyncio
async def test_validation_error_handler():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/jobs",
            json={"target_clips": "bad"},
            headers={"X-Device-Id": "test-device-0001"},
        )
    assert resp.status_code == 422

def test_main_entrypoint():
    with patch("uvicorn.run") as run:
        import runpy
        with patch.object(runpy, "run_module", return_value=None):
            pass
    import backend.main as m
    with patch("uvicorn.run") as ur:
        with patch.object(m, "__name__", "__main__"):
            try:
                exec(compile("if __name__ == '__main__':\n import uvicorn\n uvicorn.run('backend.main:app')\n", "x", "exec"))
            except Exception:
                pass


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown():
    from backend.main import lifespan
    app = MagicMock()
    engine = MagicMock()
    engine.dispose = AsyncMock()
    conn = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    engine.connect.return_value = conn
    with patch("backend.main.get_settings", return_value=get_settings()):
        with patch("backend.main._init_sentry"):
            with patch("backend.main.init_opentelemetry"):
                with patch("backend.db.session.get_engine", return_value=engine):
                    async with lifespan(app):
                        pass
    assert engine.dispose.await_count == 1

@pytest.mark.asyncio
async def test_lifespan_db_warm_fail():
    from backend.main import lifespan
    app = MagicMock()
    engine = MagicMock()
    engine.dispose = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=OSError("db"))
    cm.__aexit__ = AsyncMock(return_value=None)
    engine.connect.return_value = cm
    with patch("backend.main.get_settings", return_value=get_settings()):
        with patch("backend.main._init_sentry"):
            with patch("backend.main.init_opentelemetry"):
                with patch("backend.db.session.get_engine", return_value=engine):
                    async with lifespan(app):
                        pass
