"""Installer packaging config sanity checks (MASTER_TODO §4.10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.desktop


def test_electron_builder_includes_sidecar_staging():
    pkg = json.loads((Path("apps/desktop/package.json")).read_text(encoding="utf-8"))
    build = pkg["build"]
    extra = build.get("extraResources", [])
    assert any(
        r.get("to") == "sidecar" and ".staging/sidecar" in r.get("from", "")
        for r in extra
    ), extra


def test_electron_builder_nsis_is_configured():
    pkg = json.loads((Path("apps/desktop/package.json")).read_text(encoding="utf-8"))
    nsis = pkg["build"].get("nsis", {})
    assert nsis.get("oneClick") is False
    assert nsis.get("allowToChangeInstallationDirectory") is True


def test_installer_orchestration_scripts_exist():
    root = Path(".")
    for name in (
        "scripts/build_desktop_installer.ps1",
        "scripts/stage_sidecar_for_electron.ps1",
        "scripts/sign_windows_artifact.ps1",
        "packaging/installer/README.md",
    ):
        assert (root / name).is_file(), name
