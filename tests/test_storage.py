"""Storage helper tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.storage import S3Storage, upload_key


def test_upload_key_anonymous():
    key = upload_key(None, "abc123", "video.mp4")
    assert key == "uploads/anonymous/abc123/video.mp4"


def test_presigned_urls_use_public_endpoint():
    with patch("boto3.client") as mock_client:
        internal = MagicMock(name="internal_client")
        public = MagicMock(name="public_client")
        public.generate_presigned_url.return_value = (
            "http://localhost:9000/streamclip/clip.mp4?sig=1"
        )
        mock_client.side_effect = [internal, public]

        storage = S3Storage(
            bucket="streamclip",
            endpoint_url="http://minio:9000",
            public_base_url="http://localhost:9000",
            access_key="key",
            secret_key="secret",
        )
        internal.head_bucket.assert_called_once()

        url = storage.presigned_get_url("jobs/x/clips/clip.mp4")
        public.generate_presigned_url.assert_called_once()
        assert url.startswith("http://localhost:9000/")