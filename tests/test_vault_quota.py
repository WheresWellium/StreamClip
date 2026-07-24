"""Tests for core.vault.quota helpers."""

from __future__ import annotations

from core.vault.quota import format_bytes_human, quota_warning


def test_format_bytes_human_gb():
    assert format_bytes_human(10 * 1024**3) == "10 GB"


def test_format_bytes_human_mb():
    assert "MB" in format_bytes_human(5 * 1024**2)


def test_quota_warning_levels():
    assert quota_warning(10, 100) is None
    assert quota_warning(80, 100) == "approaching"
    assert quota_warning(95, 100) == "critical"
    assert quota_warning(100, 100) == "exceeded"
