"""Production docker-compose sanity checks (MASTER_TODO §4.14)."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_prod_compose() -> dict:
    path = Path("docker-compose.prod.yml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_prod_compose_has_distribution_env_on_api():
    compose = _load_prod_compose()
    env = compose["services"]["api"]["environment"]
    assert "STREAMCLIP_DISTRIBUTION__WEB_ORIGIN" in env
    assert "STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY" in env
    assert "STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID" in env


def test_prod_compose_mounts_assets_volume():
    compose = _load_prod_compose()
    api_vols = compose["services"]["api"]["volumes"]
    worker_vols = compose["services"]["worker"]["volumes"]
    assert any("assets_data:/app/assets" in v for v in api_vols)
    assert any("assets_data:/app/assets" in v for v in worker_vols)
    assert "assets_data" in compose["volumes"]


def test_prod_compose_worker_queues_configurable():
    compose = _load_prod_compose()
    worker_env = compose["services"]["worker"]["environment"]
    assert worker_env.get("STREAMCLIP_WORKER_QUEUES") == "${STREAMCLIP_WORKER_QUEUES:-default}"
    cmd = compose["services"]["worker"]["command"]
    assert "STREAMCLIP_WORKER_QUEUES" in cmd
    gpu = compose["services"]["gpu-worker"]
    assert gpu["profiles"] == ["gpu"]
    assert "--queues=gpu" in gpu["command"]


def test_prod_compose_cpu_safe_defaults_on_worker():
    compose = _load_prod_compose()
    env = compose["services"]["worker"]["environment"]
    assert env.get("STREAMCLIP_WHISPER__DEVICE") == "cpu"
    assert env.get("STREAMCLIP_EXPORT__CODEC") == "libx264"


def test_seed_assets_script_exists():
    assert Path("scripts/seed_assets_if_empty.py").is_file()


def test_seed_assets_populates_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STREAMCLIP_ASSETS_DIR", str(tmp_path))
    import subprocess
    import sys

    subprocess.run([sys.executable, "scripts/seed_assets_if_empty.py"], check=True, cwd=".")
    assert (tmp_path / "manifest.json").is_file()
