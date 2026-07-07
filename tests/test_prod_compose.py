"""Production docker-compose sanity checks (MASTER_TODO §4.14).

Host-only: the API container does not need to validate compose YAML.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.desktop

COMPOSE = Path("docker-compose.prod.yml")


def _compose_text() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def _load_prod_compose() -> dict:
    data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_prod_compose_declares_distribution_env():
    text = _compose_text()
    for key in (
        "STREAMCLIP_DISTRIBUTION__WEB_ORIGIN",
        "STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY",
        "STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID",
        "streamclip-distribution-env",
    ):
        assert key in text


def test_prod_compose_mounts_assets_volume():
    compose = _load_prod_compose()
    api_vols = compose["services"]["api"]["volumes"]
    worker_vols = compose["services"]["worker"]["volumes"]
    assert any("assets_data:/app/assets" in v for v in api_vols)
    assert any("assets_data:/app/assets" in v for v in worker_vols)
    assert "assets_data" in compose["volumes"]


def test_prod_compose_worker_queues_configurable():
    text = _compose_text()
    assert "STREAMCLIP_WORKER_QUEUES" in text
    assert "--queues=gpu" in text
    gpu = _load_prod_compose()["services"]["gpu-worker"]
    assert gpu["profiles"] == ["gpu"]


def test_prod_compose_cpu_safe_defaults_on_worker():
    text = _compose_text()
    assert "STREAMCLIP_WHISPER__DEVICE: cpu" in text
    assert "STREAMCLIP_EXPORT__CODEC: libx264" in text


def test_seed_assets_script_exists():
    assert Path("scripts/seed_assets_if_empty.py").is_file()


def test_seed_assets_populates_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STREAMCLIP_ASSETS_DIR", str(tmp_path))
    import subprocess
    import sys

    subprocess.run([sys.executable, "scripts/seed_assets_if_empty.py"], check=True, cwd=".")
    assert (tmp_path / "manifest.json").is_file()
