"""Upload ingest maps missing local objects to a friendly error."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import get_settings
from core.errors import IngestError
from core.ingest.resolvers.storage import download_from_storage
from core.storage import LocalStorage


def test_download_from_storage_missing_file_is_friendly(tmp_path):
    cfg = get_settings(reload=True)
    store = LocalStorage(root=tmp_path / "storage")
    dest = tmp_path / "workspace" / "source.mp4"
    with pytest.raises(IngestError) as ei:
        download_from_storage(
            "uploads/device/missing.mp4",
            dest,
            cfg,
            storage=store,
        )
    assert "uploading again" in ei.value.user_message.lower()
