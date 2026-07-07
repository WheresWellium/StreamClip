"""Tests for PyInstaller sidecar scaffold (ADR-001 §4.6)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import desktop_sidecar.run as sidecar

_DATA_ENV_KEYS = (
    "STREAMCLIP_DATABASE__URL",
    "STREAMCLIP_DATABASE__SYNC_URL",
    "STREAMCLIP_STORAGE__LOCAL_ROOT",
    "STREAMCLIP_WORKSPACE_DIR",
    "STREAMCLIP_CACHE_DIR",
)


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


def test_desktop_data_dir_dev_default_is_none(monkeypatch):
    monkeypatch.delenv("STREAMCLIP_DESKTOP_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert sidecar.desktop_data_dir() is None


def test_desktop_data_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("STREAMCLIP_DESKTOP_DATA_DIR", str(tmp_path / "data"))
    assert sidecar.desktop_data_dir() == tmp_path / "data"


def test_desktop_data_dir_frozen_uses_localappdata(tmp_path, monkeypatch):
    monkeypatch.delenv("STREAMCLIP_DESKTOP_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert sidecar.desktop_data_dir() == tmp_path / "StreamClip"


def test_desktop_data_dir_frozen_fallback_without_localappdata(monkeypatch):
    monkeypatch.delenv("STREAMCLIP_DESKTOP_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert sidecar.desktop_data_dir() == Path.home() / ".streamclip"


def test_configure_data_dirs_sets_env_and_creates_dirs(tmp_path):
    data_dir = tmp_path / "StreamClip"
    with patch.dict(os.environ):
        for key in _DATA_ENV_KEYS:
            os.environ.pop(key, None)

        sidecar.configure_data_dirs(data_dir)

        db_posix = (data_dir / "streamclip.db").as_posix()
        assert os.environ["STREAMCLIP_DATABASE__URL"] == f"sqlite+aiosqlite:///{db_posix}"
        assert os.environ["STREAMCLIP_DATABASE__SYNC_URL"] == f"sqlite:///{db_posix}"
        assert os.environ["STREAMCLIP_STORAGE__LOCAL_ROOT"] == str(data_dir / "storage")
        assert os.environ["STREAMCLIP_WORKSPACE_DIR"] == str(data_dir / "workspace")
        assert os.environ["STREAMCLIP_CACHE_DIR"] == str(data_dir / "cache")
    assert (data_dir / "workspace").is_dir()
    assert (data_dir / "storage").is_dir()
    assert (data_dir / "cache").is_dir()


def test_configure_data_dirs_respects_explicit_env(tmp_path):
    with patch.dict(os.environ):
        os.environ["STREAMCLIP_DATABASE__URL"] = "sqlite+aiosqlite:///C:/custom/app.db"
        sidecar.configure_data_dirs(tmp_path / "StreamClip")
        assert os.environ["STREAMCLIP_DATABASE__URL"] == "sqlite+aiosqlite:///C:/custom/app.db"


def test_configure_desktop_env_wires_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sidecar, "app_root", lambda: tmp_path)
    data_dir = tmp_path / "appdata"
    with patch.dict(os.environ):
        for key in _DATA_ENV_KEYS:
            os.environ.pop(key, None)
        os.environ["STREAMCLIP_DESKTOP_DATA_DIR"] = str(data_dir)

        sidecar.configure_desktop_env(tmp_path)

        assert os.environ["STREAMCLIP_STORAGE__LOCAL_ROOT"] == str(data_dir / "storage")
        assert os.environ["STREAMCLIP_WORKSPACE_DIR"] == str(data_dir / "workspace")
    assert (data_dir / "workspace").is_dir()


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
