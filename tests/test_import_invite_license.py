"""Tests for import_invite_license script helpers."""

from __future__ import annotations

import pytest

from scripts.import_invite_license import _normalize_key, _parse_tier
from backend.db.models import UserTier


def test_normalize_key_accepts_scpro_format():
    key = _normalize_key("scpro-abcd-1234-5678-9abc")
    assert key == "SCPRO-ABCD-1234-5678-9ABC"


def test_normalize_key_rejects_bad_format():
    with pytest.raises(ValueError):
        _normalize_key("SCPRO-bad")


def test_parse_tier():
    assert _parse_tier("admin") is UserTier.ADMIN
    assert _parse_tier("pro") is UserTier.PRO
