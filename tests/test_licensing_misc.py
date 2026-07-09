"""Additional licensing helpers not covered by test_license_chain.py."""

from __future__ import annotations

import json

import jwt
import pytest

from backend.db.models import UserTier
from core.config import get_settings
from core.licensing import (
    activate_license_key,
    create_entitlement_token,
    get_install_tier,
    hash_license_key,
    load_persisted_entitlement,
    verify_entitlement_token,
)


def test_hash_license_key_strips_whitespace():
    assert hash_license_key("  abc  ") == hash_license_key("abc")


def test_create_entitlement_token_defaults_expiry():
    cfg = get_settings()
    token = create_entitlement_token(
        tier=UserTier.PRO,
        machine_id="m1",
        license_key_hash=hash_license_key("key"),
        expires_at=None,
        cfg=cfg,
    )
    ent = verify_entitlement_token(token, machine_id="m1", cfg=cfg)
    assert ent.tier is UserTier.PRO


def test_verify_entitlement_rejects_bad_token():
    cfg = get_settings()
    with pytest.raises(ValueError, match="Invalid"):
        verify_entitlement_token("not-a-jwt", machine_id="m1", cfg=cfg)


def test_verify_entitlement_rejects_wrong_type(tmp_path):
    cfg = get_settings()
    payload = {"type": "access", "tier": "pro", "machine_id": "m1", "license_key_hash": "x"}
    token = jwt.encode(payload, cfg.auth.secret_key, algorithm=cfg.auth.algorithm)
    with pytest.raises(ValueError, match="Wrong token"):
        verify_entitlement_token(token, machine_id="m1", cfg=cfg)


def test_activate_rejects_short_key():
    with pytest.raises(ValueError, match="Invalid license"):
        activate_license_key("short", "machine-1", tier=UserTier.PRO)


def test_load_persisted_entitlement_missing_file(tmp_path):
    cfg = get_settings()
    old = cfg.licensing.license_file
    cfg.licensing.license_file = tmp_path / "missing.json"
    try:
        assert load_persisted_entitlement(cfg) is None
    finally:
        cfg.licensing.license_file = old


def test_load_persisted_entitlement_bad_json(tmp_path):
    cfg = get_settings()
    old = cfg.licensing.license_file
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    cfg.licensing.license_file = path
    try:
        assert load_persisted_entitlement(cfg) is None
    finally:
        cfg.licensing.license_file = old


def test_get_install_tier_disabled(monkeypatch, tmp_path):
    cfg = get_settings()
    old_enabled = cfg.licensing.enabled
    old_file = cfg.licensing.license_file
    cfg.licensing.enabled = False
    cfg.licensing.license_file = tmp_path / "license.json"
    try:
        assert get_install_tier("machine-1", cfg) is UserTier.FREE
    finally:
        cfg.licensing.enabled = old_enabled
        cfg.licensing.license_file = old_file


def test_get_install_tier_from_persisted_file(tmp_path):
    cfg = get_settings()
    old_enabled = cfg.licensing.enabled
    old_file = cfg.licensing.license_file
    cfg.licensing.enabled = True
    cfg.licensing.license_file = tmp_path / "license.json"
    try:
        token, _ = activate_license_key("SCPRO-AAAA-BBBB-CCCC-DDDD", "machine-x", tier=UserTier.ADMIN, cfg=cfg)
        cfg.licensing.license_file.write_text(json.dumps({"entitlement_jwt": token}), encoding="utf-8")
        assert get_install_tier("machine-x", cfg) is UserTier.ADMIN
        assert get_install_tier("wrong-machine", cfg) is UserTier.FREE
    finally:
        cfg.licensing.enabled = old_enabled
        cfg.licensing.license_file = old_file


def test_get_install_tier_enabled_but_no_file(tmp_path):
    cfg = get_settings()
    old_enabled = cfg.licensing.enabled
    old_file = cfg.licensing.license_file
    cfg.licensing.enabled = True
    cfg.licensing.license_file = tmp_path / "absent.json"
    try:
        assert get_install_tier("machine-1", cfg) is UserTier.FREE
    finally:
        cfg.licensing.enabled = old_enabled
        cfg.licensing.license_file = old_file


def test_load_persisted_entitlement_missing_jwt_key(tmp_path):
    cfg = get_settings()
    old = cfg.licensing.license_file
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"other": "x"}), encoding="utf-8")
    cfg.licensing.license_file = path
    try:
        assert load_persisted_entitlement(cfg) is None
    finally:
        cfg.licensing.license_file = old


def test_load_persisted_entitlement_returns_token(tmp_path):
    cfg = get_settings()
    old = cfg.licensing.license_file
    path = tmp_path / "ok.json"
    path.write_text(json.dumps({"entitlement_jwt": "tok-abc"}), encoding="utf-8")
    cfg.licensing.license_file = path
    try:
        assert load_persisted_entitlement(cfg) == "tok-abc"
    finally:
        cfg.licensing.license_file = old


def test_verify_entitlement_allows_missing_exp():
    cfg = get_settings()
    payload = {
        "type": "entitlement",
        "tier": UserTier.PRO.value,
        "machine_id": "m1",
        "license_key_hash": "abc",
    }
    token = jwt.encode(payload, cfg.auth.secret_key, algorithm=cfg.auth.algorithm)
    ent = verify_entitlement_token(token, machine_id="m1", cfg=cfg)
    assert ent.expires_at is None
    assert ent.tier is UserTier.PRO
