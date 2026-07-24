"""Vault quota helpers — warning thresholds and human-readable byte sizes."""

from __future__ import annotations

from typing import Literal

QuotaWarning = Literal["approaching", "critical", "exceeded"] | None

WARN_AT_PCT = 75
CRITICAL_AT_PCT = 90

_GB = 1024**3


def format_bytes_human(num_bytes: int) -> str:
    """Format byte counts for API responses (e.g. ``7.0 GB``)."""
    if num_bytes < 0:
        num_bytes = 0
    if num_bytes >= _GB:
        value = num_bytes / _GB
        return f"{value:.1f} GB" if value < 10 else f"{round(value)} GB"
    mb = num_bytes / (1024**2)
    if mb >= 1:
        return f"{mb:.1f} MB"
    kb = num_bytes / 1024
    if kb >= 1:
        return f"{round(kb)} KB"
    return f"{num_bytes} B"


def quota_warning(used: int, limit: int) -> QuotaWarning:
    """Map usage to warning level per TDD §7.1.5."""
    if limit <= 0:
        return None
    if used >= limit:
        return "exceeded"
    pct = (used / limit) * 100
    if pct >= CRITICAL_AT_PCT:
        return "critical"
    if pct >= WARN_AT_PCT:
        return "approaching"
    return None
