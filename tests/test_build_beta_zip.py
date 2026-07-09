"""Unit tests for the tester-facing beta .zip builder."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scripts import build_beta_zip


def test_should_include_excludes_dev_only_paths() -> None:
    assert not build_beta_zip._should_include(".github/workflows/test.yml")
    assert not build_beta_zip._should_include(".cursor/rules/foo.mdc")
    assert not build_beta_zip._should_include("tests/test_foo.py")
    assert not build_beta_zip._should_include("AGENTS.md")


def test_should_include_keeps_runtime_files() -> None:
    assert build_beta_zip._should_include("docker-compose.yml")
    assert build_beta_zip._should_include("Dockerfile")
    assert build_beta_zip._should_include(".env.example")
    assert build_beta_zip._should_include("backend/main.py")
    assert build_beta_zip._should_include("scripts/start_local.ps1")


def test_build_zip_produces_valid_archive_without_secrets(tmp_path: Path) -> None:
    out_path = tmp_path / "StreamClip-beta.zip"
    code = build_beta_zip.build_zip(ref="HEAD", out_path=out_path)
    assert code == 0
    assert out_path.is_file()

    with zipfile.ZipFile(out_path) as zf:
        names = zf.namelist()
        assert any(n.endswith("docker-compose.yml") for n in names)
        assert any(n.endswith(".env.example") for n in names)
        assert not any(n.endswith(".env") and not n.endswith(".env.example") for n in names)
        assert not any("tmp/" in n for n in names)
        assert not any(".github/" in n for n in names)
        assert not any(".cursor/" in n for n in names)
