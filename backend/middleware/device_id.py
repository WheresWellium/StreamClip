"""Normalize browser device IDs to fit String(32) DB columns."""

from __future__ import annotations


def normalize_device_id(device_id: str) -> str:
    return device_id.replace("-", "")[:32]
