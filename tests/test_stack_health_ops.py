"""Tests for autonomous stack health probes (OPS_WEBHOOK stack_degraded)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.config import get_settings
from core.notify import stack_health as sh
from core.tasks import notify_tasks as nt


def setup_function() -> None:
    sh.reset_stack_alert_state()


def teardown_function() -> None:
    sh.reset_stack_alert_state()


def test_should_emit_stack_alert_edge_and_cooldown():
    assert sh.should_emit_stack_alert("degraded", now=100.0) is True
    assert sh.should_emit_stack_alert("degraded", now=110.0) is False
    assert sh.should_emit_stack_alert("degraded", now=100.0 + sh._COOLDOWN_SECS) is True
    assert sh.should_emit_stack_alert("ok", now=200.0) is False
    assert sh.should_emit_stack_alert("degraded", now=201.0) is True


def test_probe_stack_dependencies_all_ok(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    storage = MagicMock()

    with (
        patch("sqlalchemy.create_engine", return_value=engine),
        patch("core.storage.make_storage", return_value=storage),
    ):
        result = sh.probe_stack_dependencies(cfg)

    assert result["status"] == "ok"
    assert result["checks"]["database"] is True
    assert result["checks"]["redis"] is True
    assert result["checks"]["storage"] is True
    assert result["failures"] == []


def test_probe_stack_dependencies_db_fail(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    storage = MagicMock()

    with (
        patch("sqlalchemy.create_engine", side_effect=RuntimeError("db down")),
        patch("core.storage.make_storage", return_value=storage),
    ):
        result = sh.probe_stack_dependencies(cfg)

    assert result["status"] == "degraded"
    assert result["checks"]["database"] is False
    assert any("database" in f for f in result["failures"])


def test_probe_stack_health_ops_alert_ok_no_webhook():
    with (
        patch(
            "core.notify.stack_health.probe_stack_dependencies",
            return_value={"status": "ok", "checks": {}, "failures": []},
        ),
        patch.object(nt, "post_ops_webhook") as post,
    ):
        out = nt.probe_stack_health_ops_alert()
    assert out["status"] == "ok"
    assert out["alerted"] is False
    post.assert_not_called()


def test_probe_stack_dependencies_redis_fail_when_not_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    storage = MagicMock()

    with (
        patch("sqlalchemy.create_engine", return_value=engine),
        patch("core.storage.make_storage", return_value=storage),
        patch("redis.from_url", side_effect=RuntimeError("redis down")),
    ):
        result = sh.probe_stack_dependencies(cfg)

    assert result["status"] == "degraded"
    assert result["checks"]["redis"] is False
    assert any("redis" in f for f in result["failures"])


def test_probe_stack_dependencies_redis_ok_when_not_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    storage = MagicMock()
    redis_client = MagicMock()

    with (
        patch("sqlalchemy.create_engine", return_value=engine),
        patch("core.storage.make_storage", return_value=storage),
        patch("redis.from_url", return_value=redis_client),
    ):
        result = sh.probe_stack_dependencies(cfg)

    assert result["checks"]["redis"] is True
    redis_client.ping.assert_called_once()
    redis_client.close.assert_called_once()


def test_probe_stack_dependencies_storage_fail(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    storage = MagicMock()
    storage.list_prefix.side_effect = RuntimeError("storage down")

    with (
        patch("sqlalchemy.create_engine", return_value=engine),
        patch("core.storage.make_storage", return_value=storage),
    ):
        result = sh.probe_stack_dependencies(cfg)

    assert result["status"] == "degraded"
    assert result["checks"]["storage"] is False
    assert any("storage" in f for f in result["failures"])


def test_probe_stack_health_ops_alert_degraded_posts_once():
    degraded = {
        "status": "degraded",
        "checks": {"database": False, "redis": True, "storage": True},
        "failures": ["database: down"],
    }
    with (
        patch(
            "core.notify.stack_health.probe_stack_dependencies",
            return_value=degraded,
        ),
        patch.object(nt, "post_ops_webhook", return_value=True) as post,
    ):
        first = nt.probe_stack_health_ops_alert()
        second = nt.probe_stack_health_ops_alert()
    assert first["alerted"] is True
    assert first["event"] == "stack_degraded"
    assert second["alerted"] is False
    assert second.get("reason") == "cooldown"
    post.assert_called_once()
    payload = post.call_args[0][0]
    assert payload["event"] == "stack_degraded"
    assert payload["checks"]["database"] is False
