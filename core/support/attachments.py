"""Support attachment limits and storage keys (TDD §13.2)."""

from __future__ import annotations

MAX_ATTACHMENTS_PER_REPORT = 3
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024

ALLOWED_SUPPORT_ATTACHMENT_TYPES = frozenset({
    "image/png",
    "image/jpeg",
    "image/webp",
    "text/plain",
    "application/json",
})


def support_attachment_key(owner: str, attachment_id: str, filename: str) -> str:
    safe_owner = owner or "anonymous"
    return f"support/attachments/{safe_owner}/{attachment_id}/{filename}"
