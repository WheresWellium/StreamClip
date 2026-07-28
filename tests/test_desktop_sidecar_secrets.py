"""Desktop sidecar W2/W3: install secrets and bundled license seed."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.desktop

from alembic import command
from alembic.config import Config

from backend.db.repositories import InstallLicenseRepository
from backend.db.session import db_session, dispose_engine, get_sync_engine_url
from core.config import get_settings, is_weak_auth_secret
from core.licensing import hash_license_key
from desktop_sidecar import install_secrets, seed_licenses


def test_ensure_install_secrets_creates_and_reuses(tmp_path: Path) -> None:
    data_dir = tmp_path / "StreamClip"
    with patch.dict(os.environ, clear=False):
        os.environ.pop("STREAMCLIP_AUTH__SECRET_KEY", None)
        os.environ.pop("STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY", None)
        install_secrets.ensure_install_secrets(data_dir)
        auth1 = os.environ["STREAMCLIP_AUTH__SECRET_KEY"]
        token1 = os.environ["STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY"]
        assert not is_weak_auth_secret(auth1)
        assert token1

        os.environ.pop("STREAMCLIP_AUTH__SECRET_KEY", None)
        os.environ.pop("STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY", None)
        install_secrets.ensure_install_secrets(data_dir)
        assert os.environ["STREAMCLIP_AUTH__SECRET_KEY"] == auth1
        assert os.environ["STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY"] == token1


def test_ensure_install_secrets_respects_explicit_env(tmp_path: Path) -> None:
    data_dir = tmp_path / "StreamClip"
    with patch.dict(os.environ, clear=False):
        os.environ["STREAMCLIP_AUTH__SECRET_KEY"] = "explicit-auth-secret-value-32chars!"
        os.environ["STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY"] = "explicit-token"
        install_secrets.ensure_install_secrets(data_dir)
        assert os.environ["STREAMCLIP_AUTH__SECRET_KEY"] == "explicit-auth-secret-value-32chars!"


@pytest.mark.asyncio
async def test_seed_bundled_licenses_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "streamclip.db"
    db_posix = db_path.resolve().as_posix()
    monkeypatch.setenv("STREAMCLIP_DATABASE__URL", f"sqlite+aiosqlite:///{db_posix}")
    monkeypatch.setenv("STREAMCLIP_DATABASE__SYNC_URL", f"sqlite:///{db_posix}")
    get_settings(reload=True)

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", get_sync_engine_url())
    command.upgrade(alembic_cfg, "head")

    license_key = "SCPRO-AAAA-BBBB-CCCC-DDDD"
    seed_path = tmp_path / "packaging" / "cohort" / "cohort_licenses.json"
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text(
        json.dumps(
            {
                "version": 1,
                "licenses": [{"key_hash": hash_license_key(license_key), "tier": "admin"}],
            },
        ),
        encoding="utf-8",
    )

    assert seed_licenses.seed_bundled_licenses(tmp_path) == 1
    assert seed_licenses.seed_bundled_licenses(tmp_path) == 0

    await dispose_engine()
    async with db_session() as session:
        repo = InstallLicenseRepository(session)
        lic = await repo.get_by_key_hash(hash_license_key(license_key))
        assert lic is not None
        assert lic.status == "issued"
    await dispose_engine()
    get_settings(reload=True)


def test_configure_desktop_env_calls_install_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import desktop_sidecar.run as sidecar

    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "config" / "desktop.yaml"
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("queue:\n  backend: inprocess\n", encoding="utf-8")
    monkeypatch.setattr(sidecar, "app_root", lambda: tmp_path)
    monkeypatch.setenv("STREAMCLIP_DESKTOP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    with patch("desktop_sidecar.install_secrets.ensure_install_secrets") as ensure:
        sidecar.configure_desktop_env(tmp_path)
        ensure.assert_called_once_with(tmp_path / "data")
