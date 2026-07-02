"""Overlay asset manifest tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.overlay import load_manifest, records_from_db_assets


def test_load_manifest_from_assets():
    assets = Path(__file__).resolve().parents[1] / "assets"
    if not (assets / "manifest.json").exists():
        return
    records = load_manifest(assets)
    assert len(records) >= 1


class _FakeStorage:
    def __init__(self) -> None:
        self.downloads: list[str] = []

    def download(self, key: str, dest: Path, on_progress=None) -> None:
        self.downloads.append(key)
        dest.write_bytes(b"gif")


def _db_asset(**overrides) -> SimpleNamespace:
    base = dict(
        id="asset-1",
        asset_type="gif",
        storage_key="assets/user/hype.gif",
        sfx_storage_key=None,
        description="absolute hype moment",
        tags=["hype"],
        default_duration_secs=2.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_records_from_db_assets_downloads_and_caches(tmp_path):
    storage = _FakeStorage()
    cache = tmp_path / "db_assets"

    records = records_from_db_assets([_db_asset()], storage, cache)
    assert len(records) == 1
    assert records[0].description == "absolute hype moment"
    assert records[0].path.exists()
    assert storage.downloads == ["assets/user/hype.gif"]

    # Second call (e.g. next clip in the same job) hits the cache, no re-fetch
    records_from_db_assets([_db_asset()], storage, cache)
    assert storage.downloads == ["assets/user/hype.gif"]


def test_records_from_db_assets_skips_failed_downloads(tmp_path):
    class FailingStorage:
        def download(self, key: str, dest: Path, on_progress=None) -> None:
            raise OSError("bucket unavailable")

    records = records_from_db_assets(
        [_db_asset(), _db_asset(id="asset-2")],
        FailingStorage(),
        tmp_path / "db_assets",
    )
    assert records == []  # overlays degrade; render must not fail
