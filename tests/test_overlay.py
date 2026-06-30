"""Overlay asset manifest tests."""

from __future__ import annotations

from pathlib import Path

from core.overlay import load_manifest


def test_load_manifest_from_assets():
    assets = Path(__file__).resolve().parents[1] / "assets"
    if not (assets / "manifest.json").exists():
        return
    records = load_manifest(assets)
    assert len(records) >= 1
