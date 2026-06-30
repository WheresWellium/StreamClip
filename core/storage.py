"""
StreamClip — Storage Abstraction

A single interface over local filesystem, S3, and MinIO so the rest of the
codebase never branches on backend. The frontend never touches the API for
video bytes — it gets a presigned URL and talks directly to storage.

Architecture:
  • Backend writes only metadata (paths, sizes, hashes) to Postgres.
  • Source videos and rendered clips live in object storage under
    `jobs/{job_id}/{stage}/{filename}`.
  • Presigned URLs expire in 1 hour by default.
"""

from __future__ import annotations

import io
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

import structlog

from core.config import Settings
from core.errors import StorageError

log = structlog.get_logger(__name__)


# ─── Interface ──────────────────────────────────────────────────────────────

class Storage(ABC):
    @abstractmethod
    def upload(self, key: str, data: BinaryIO | bytes | Path,
               content_type: str = "application/octet-stream") -> str:
        """Upload bytes / file / Path. Returns the storage key."""

    @abstractmethod
    def download(self, key: str, dest: Path) -> Path:
        """Download to a local path. Returns the destination."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an object."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if an object exists."""

    @abstractmethod
    def presigned_get_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a time-limited download URL."""

    @abstractmethod
    def presigned_put_url(self, key: str, expires_in: int = 3600,
                          content_type: str = "video/mp4") -> str:
        """Generate a time-limited upload URL (for direct browser → storage)."""

    @abstractmethod
    def list_prefix(self, prefix: str) -> list[str]:
        """List all keys under a prefix."""

    @abstractmethod
    def size(self, key: str) -> int:
        """Return object size in bytes."""


# ─── Local filesystem (dev / single-user) ───────────────────────────────────

class LocalStorage(Storage):
    """Local filesystem backend. Presigned URLs return file:// for dev."""

    def __init__(self, root: Path, public_base_url: str = "") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base_url = public_base_url.rstrip("/")

    def _abs(self, key: str) -> Path:
        # Sanitise: no leading slashes, no .. traversal
        clean = key.lstrip("/").replace("..", "")
        p = (self.root / clean).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise StorageError(f"Path traversal blocked: {key!r}")
        return p

    def upload(self, key: str, data: BinaryIO | bytes | Path,
               content_type: str = "application/octet-stream") -> str:
        dest = self._abs(key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, (str, Path)):
            shutil.copy2(str(data), dest)
        elif isinstance(data, bytes):
            dest.write_bytes(data)
        else:
            with open(dest, "wb") as fh:
                shutil.copyfileobj(data, fh)
        log.debug("local_upload", key=key, size=dest.stat().st_size)
        return key

    def download(self, key: str, dest: Path) -> Path:
        src = self._abs(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest

    def delete(self, key: str) -> None:
        p = self._abs(key)
        if p.exists():
            p.unlink()

    def exists(self, key: str) -> bool:
        return self._abs(key).exists()

    def presigned_get_url(self, key: str, expires_in: int = 3600) -> str:
        # In production, this should route through a signed token endpoint;
        # for local dev we serve directly via FastAPI /storage route.
        return f"{self.public_base_url}/storage/{key}" if self.public_base_url \
            else f"/storage/{key}"

    def presigned_put_url(self, key: str, expires_in: int = 3600,
                          content_type: str = "video/mp4") -> str:
        return f"{self.public_base_url}/storage/{key}?upload=1" if self.public_base_url \
            else f"/storage/{key}?upload=1"

    def list_prefix(self, prefix: str) -> list[str]:
        base = self._abs(prefix)
        if not base.exists():
            return []
        return [
            str(p.relative_to(self.root)).replace("\\", "/")
            for p in base.rglob("*") if p.is_file()
        ]

    def size(self, key: str) -> int:
        return self._abs(key).stat().st_size


# ─── S3 / MinIO backend (production) ────────────────────────────────────────

class S3Storage(Storage):
    """boto3-backed S3 / MinIO storage."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise StorageError("boto3 not installed; pip install boto3") from exc

        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

        # Ensure bucket exists (idempotent)
        try:
            self._client.head_bucket(Bucket=bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=bucket)
                log.info("s3_bucket_created", bucket=bucket)
            except Exception as exc:
                log.warning("s3_bucket_create_failed", bucket=bucket, error=str(exc))

    def upload(self, key: str, data: BinaryIO | bytes | Path,
               content_type: str = "application/octet-stream") -> str:
        try:
            if isinstance(data, (str, Path)):
                self._client.upload_file(
                    str(data), self.bucket, key,
                    ExtraArgs={"ContentType": content_type},
                )
            elif isinstance(data, bytes):
                self._client.put_object(
                    Bucket=self.bucket, Key=key,
                    Body=data, ContentType=content_type,
                )
            else:
                self._client.upload_fileobj(
                    data, self.bucket, key,
                    ExtraArgs={"ContentType": content_type},
                )
            log.debug("s3_upload", key=key)
            return key
        except Exception as exc:
            raise StorageError(f"Upload failed for {key}") from exc

    def download(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._client.download_file(self.bucket, key, str(dest))
            return dest
        except Exception as exc:
            raise StorageError(f"Download failed for {key}") from exc

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def presigned_get_url(self, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def presigned_put_url(self, key: str, expires_in: int = 3600,
                          content_type: str = "video/mp4") -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

    def list_prefix(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def size(self, key: str) -> int:
        resp = self._client.head_object(Bucket=self.bucket, Key=key)
        return resp["ContentLength"]


# ─── Factory ────────────────────────────────────────────────────────────────

def make_storage(cfg: Settings) -> Storage:
    backend = cfg.storage.backend
    if backend == "local":
        return LocalStorage(
            root=cfg.storage.local_root,
            public_base_url=cfg.storage.public_base_url,
        )
    if backend in ("s3", "minio"):
        return S3Storage(
            bucket=cfg.storage.bucket,
            endpoint_url=cfg.storage.endpoint_url,
            access_key=cfg.storage.access_key,
            secret_key=cfg.storage.secret_key,
            region=cfg.storage.region,
        )
    raise StorageError(f"Unknown storage backend: {backend!r}")


# ─── Key helpers ────────────────────────────────────────────────────────────

def job_key(job_id: str, stage: str, filename: str) -> str:
    """Canonical key layout: jobs/{job_id}/{stage}/{filename}"""
    return f"jobs/{job_id}/{stage}/{filename}"


def upload_key(user_id: str, upload_id: str, filename: str) -> str:
    return f"uploads/{user_id}/{upload_id}/{filename}"
