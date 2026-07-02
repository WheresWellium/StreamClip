"""Extended storage coverage."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import get_settings
from core.errors import StorageError
from core.storage import LocalStorage, S3Storage, job_key, make_storage


def test_job_key():
    assert job_key("j", "clips", "a.mp4") == "jobs/j/clips/a.mp4"


def test_local_storage_download_progress(tmp_path):
    store = LocalStorage(tmp_path)
    store.upload("a/b.txt", b"hello")
    dest = tmp_path / "out.txt"
    seen: list[tuple[int, int]] = []
    store.download("a/b.txt", dest, on_progress=lambda done, total: seen.append((done, total)))
    assert dest.read_text() == "hello"
    assert seen[-1] == (5, 5)


def test_local_storage_roundtrip(tmp_path):
    store = LocalStorage(tmp_path, public_base_url="http://localhost")
    store.upload("a/b.txt", b"hello")
    assert store.exists("a/b.txt")
    assert store.size("a/b.txt") == 5
    assert "http://localhost/storage/a/b.txt" in store.presigned_get_url("a/b.txt")
    assert "upload=1" in store.presigned_put_url("a/b.txt")
    dest = tmp_path / "out.txt"
    store.download("a/b.txt", dest)
    assert dest.read_text() == "hello"
    store.upload("c/d.bin", io.BytesIO(b"xy"))
    assert store.list_prefix("a") == ["a/b.txt"]
    store.delete("a/b.txt")
    assert not store.exists("a/b.txt")


def test_local_storage_path_from_file(tmp_path):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"vid")
    store = LocalStorage(tmp_path)
    store.upload("v.mp4", src)
    assert store.exists("v.mp4")


def test_local_storage_traversal_blocked(tmp_path):
    store = LocalStorage(tmp_path)
    with pytest.raises(StorageError):
        store._abs("../escape")


def test_make_storage_local(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "local")
    monkeypatch.setattr(cfg.storage, "local_root", tmp_path)
    s = make_storage(cfg)
    assert isinstance(s, LocalStorage)


def test_make_storage_unknown():
    cfg = get_settings(reload=True)
    cfg.storage.backend = "nope"  # type: ignore[assignment]
    with pytest.raises(StorageError):
        make_storage(cfg)


def test_s3_storage_full_mock():
    with patch("boto3.client") as mock_client:
        client = MagicMock()
        presign = MagicMock()
        mock_client.return_value = client
        client.head_bucket.side_effect = Exception("no bucket")
        client.create_bucket.return_value = None

        storage = S3Storage(bucket="b", endpoint_url="http://s3")
        storage._presign_client = presign
        presign.generate_presigned_url.return_value = "http://u"

        storage.upload("k", b"data")
        storage.upload("k2", Path("/tmp/x"))
        storage.upload("k3", io.BytesIO(b"z"))

        dest = Path("/tmp/out")
        with patch.object(Path, "mkdir"):
            storage.download("k", dest)

        storage.delete("k")
        client.head_object.return_value = {}
        assert storage.exists("k")
        client.head_object.side_effect = Exception("missing")
        assert not storage.exists("k2")
        client.head_object.side_effect = None
        client.head_object.return_value = {"ContentLength": 9}

        storage.presigned_get_url("k")
        storage.presigned_put_url("k")

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [{"Contents": [{"Key": "a"}]}]
        assert storage.list_prefix("p") == ["a"]

        assert storage.size("k") == 9


def test_s3_import_error():
    with patch.dict("sys.modules", {"boto3": None}):
        with pytest.raises(StorageError):
            S3Storage(bucket="b")


def test_s3_upload_failure():
    with patch("boto3.client") as mock_client:
        client = MagicMock()
        mock_client.return_value = client
        client.head_bucket.return_value = None
        client.put_object.side_effect = RuntimeError("fail")
        storage = S3Storage(bucket="b")
        with pytest.raises(StorageError):
            storage.upload("k", b"x")


def test_s3_download_progress_accumulates():
    with patch("boto3.client") as mock_client:
        client = MagicMock()
        mock_client.return_value = client
        client.head_bucket.return_value = None
        client.head_object.return_value = {"ContentLength": 100}

        storage = S3Storage(bucket="b", endpoint_url="http://s3")
        seen: list[tuple[int, int]] = []

        def _download(bucket, key, filename, Callback=None):
            if Callback:
                Callback(40)
                Callback(60)

        client.download_file.side_effect = _download
        dest = Path("/tmp/out")
        with patch.object(Path, "mkdir"):
            storage.download("k", dest, on_progress=lambda done, total: seen.append((done, total)))
        assert seen == [(40, 100), (100, 100)]


def test_s3_download_failure():
    with patch("boto3.client") as mock_client:
        client = MagicMock()
        mock_client.return_value = client
        client.head_bucket.return_value = None
        client.download_file.side_effect = RuntimeError("fail")
        storage = S3Storage(bucket="b")
        with pytest.raises(StorageError):
            storage.download("k", Path("/tmp/x"))


def test_s3_separate_presign_client():
    with patch("boto3.client") as mock_client:
        internal = MagicMock()
        public = MagicMock()
        mock_client.side_effect = [internal, public]
        S3Storage(
            bucket="b",
            endpoint_url="http://internal",
            public_base_url="http://public",
        )
        assert mock_client.call_count == 2
