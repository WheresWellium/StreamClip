"""Tests for PyInstaller sidecar scaffold (ADR-001 §4.6)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import desktop_sidecar.run as sidecar


def test_app_root_in_dev():
    root = sidecar.app_root()
    assert (root / "backend").is_dir()
    assert (root / "desktop_sidecar" / "run.py").is_file()


def test_configure_desktop_env_sets_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "config" / "desktop.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("queue:\n  backend: inprocess\n", encoding="utf-8")
    monkeypatch.setattr(sidecar, "app_root", lambda: tmp_path)
    sidecar.configure_desktop_env(tmp_path)
    assert "STREAMCLIP_CONFIG" in __import__("os").environ


def test_run_migrations_calls_alembic(tmp_path, monkeypatch):
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = alembic\n", encoding="utf-8")
    (tmp_path / "alembic").mkdir()
    monkeypatch.setattr("backend.db.session.get_sync_engine_url", lambda: "sqlite:///./test.db")
    with patch("alembic.command.upgrade") as upgrade:
        sidecar.run_migrations(tmp_path)
        upgrade.assert_called_once()


def test_run_server_invokes_uvicorn(monkeypatch):
    monkeypatch.setenv("STREAMCLIP_SIDECAR_SKIP_MIGRATE", "1")
    with patch.object(sidecar, "configure_desktop_env") as cfg:
        with patch("uvicorn.run") as uvicorn_run:
            sidecar.run_server(host="127.0.0.1", port=9999, root=Path("."))
            cfg.assert_called_once()
            uvicorn_run.assert_called_once()
            assert uvicorn_run.call_args.kwargs.get("port") == 9999
