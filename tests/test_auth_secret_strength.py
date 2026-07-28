"""GAP O8 — weak / placeholder AUTH secret hardening."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import (
    AUTH_SECRET_MIN_LENGTH,
    auth_secret_weak_reason,
    get_settings,
    is_weak_auth_secret,
)


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "   ",
        "CHANGE_ME_IN_PRODUCTION",
        "change-me-in-production-use-openssl-rand",
        "change-me-in-production",
        "secret",
        "changeme",
        "Change-Me-Please-This-Is-Long-Enough-But-Placeholder",
        "x" * (AUTH_SECRET_MIN_LENGTH - 1),
    ],
)
def test_is_weak_auth_secret_detects_placeholders_and_short(secret: str) -> None:
    assert is_weak_auth_secret(secret) is True


def test_is_weak_auth_secret_accepts_strong_key() -> None:
    # 64 hex chars — openssl rand -hex 32
    strong = "a" * 64
    assert len(strong) >= AUTH_SECRET_MIN_LENGTH
    assert is_weak_auth_secret(strong) is False


@pytest.mark.parametrize(
    ("secret", "reason"),
    [
        ("", "missing"),
        ("CHANGE_ME_IN_PRODUCTION", "placeholder"),
        ("change-me-use-openssl-rand-hex-32", "placeholder"),
        ("x" * (AUTH_SECRET_MIN_LENGTH - 1), "too_short"),
    ],
)
def test_auth_secret_weak_reason_is_non_secret(secret: str, reason: str) -> None:
    assert auth_secret_weak_reason(secret) == reason


@pytest.mark.parametrize(
    "secret",
    [
        "CHANGE_ME_IN_PRODUCTION",
        "change-me-in-production-use-openssl-rand",
        "x" * (AUTH_SECRET_MIN_LENGTH - 1),
    ],
)
def test_non_dev_rejects_weak_auth_secret(monkeypatch, secret: str) -> None:
    monkeypatch.setenv("STREAMCLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("STREAMCLIP_AUTH__SECRET_KEY", secret)

    with pytest.raises(ValueError, match="STREAMCLIP_AUTH__SECRET_KEY"):
        get_settings(reload=True)


def test_non_dev_rejects_unset_auth_secret_default(monkeypatch) -> None:
    monkeypatch.setenv("STREAMCLIP_ENVIRONMENT", "staging")
    monkeypatch.delenv("STREAMCLIP_AUTH__SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="reason=placeholder"):
        get_settings(reload=True)


def test_non_dev_rejects_blank_auth_secret(monkeypatch) -> None:
    monkeypatch.setenv("STREAMCLIP_ENVIRONMENT", "staging")
    monkeypatch.setenv("STREAMCLIP_AUTH__SECRET_KEY", "")

    with pytest.raises(ValueError, match="reason=missing"):
        get_settings(reload=True)


def test_non_dev_accepts_strong_auth_secret(monkeypatch) -> None:
    strong = "a" * 64
    monkeypatch.setenv("STREAMCLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("STREAMCLIP_AUTH__SECRET_KEY", strong)

    cfg = get_settings(reload=True)

    assert cfg.environment == "production"
    assert cfg.auth.secret_key == strong


def test_lifespan_warns_on_dev_placeholder(monkeypatch) -> None:
    """Development remains bootable, but logs once without leaking the secret."""
    import backend.main as main_mod

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "environment", "development")
    monkeypatch.setattr(
        cfg.auth,
        "secret_key",
        "change-me-in-production-use-openssl-rand",
    )
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    monkeypatch.setattr(main_mod, "get_settings", lambda: cfg)

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    engine = MagicMock()
    engine.connect = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    engine.dispose = AsyncMock()

    with patch.object(main_mod.log, "warning") as warn, patch.object(
        main_mod, "_init_sentry"
    ), patch.object(main_mod, "init_opentelemetry"), patch(
        "backend.db.session.get_engine", return_value=engine
    ):
        app = main_mod.create_app()

        async def _run_lifespan() -> None:
            async with app.router.lifespan_context(app):
                pass

        asyncio.run(_run_lifespan())
        warn.assert_called_once()
        event = warn.call_args.args[0] if warn.call_args.args else warn.call_args.kwargs.get("event")
        assert event == "SECURITY_WARNING"
        assert warn.call_args.kwargs["auth_secret_issue"] == "placeholder"
        assert "change-me" not in warn.call_args.kwargs["message"]


def test_lifespan_skips_warning_for_strong_secret(monkeypatch) -> None:
    import backend.main as main_mod

    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "environment", "development")
    monkeypatch.setattr(cfg.auth, "secret_key", "a" * 64)
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    monkeypatch.setattr(main_mod, "get_settings", lambda: cfg)

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    engine = MagicMock()
    engine.connect = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    engine.dispose = AsyncMock()

    with patch.object(main_mod.log, "warning") as warn, patch.object(
        main_mod, "_init_sentry"
    ), patch.object(main_mod, "init_opentelemetry"), patch(
        "backend.db.session.get_engine", return_value=engine
    ):
        app = main_mod.create_app()

        async def _run_lifespan() -> None:
            async with app.router.lifespan_context(app):
                pass

        asyncio.run(_run_lifespan())
        for call in warn.call_args_list:
            assert call.args[0] != "SECURITY_WARNING"
