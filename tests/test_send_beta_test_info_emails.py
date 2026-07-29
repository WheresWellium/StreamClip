"""Unit tests for BETA TEST INFO email script (keys reuse + henna flow)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import send_beta_test_info_emails as sender

CHECKOUT_BASE = "https://store.lemonsqueezy.com/checkout/buy/12345"
HENNA = "https://streamclip-henna.vercel.app"


def test_parse_keys_csv_maps_email_to_key(tmp_path: Path) -> None:
    path = tmp_path / "keys.csv"
    path.write_text(
        "email,license_key,order_id,tier\n"
        "a@example.com,SCPRO-AAAA-BBBB-CCCC-DDDD,beta-phase0-regen-001,admin\n",
        encoding="utf-8",
    )
    keys = sender._parse_keys_csv(path)
    assert keys["a@example.com"] == "SCPRO-AAAA-BBBB-CCCC-DDDD"


def test_build_cohort_manual_requires_existing_keys(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\ntester@example.com,Tester\n", encoding="utf-8")
    keys = tmp_path / "keys.csv"
    keys.write_text(
        "email,license_key,order_id,tier\n"
        "tester@example.com,SCPRO-1111-2222-3333-4444,beta-phase0-regen-001,admin\n",
        encoding="utf-8",
    )
    members = sender._build_cohort(
        cohort, keys, mode="manual", checkout_base=CHECKOUT_BASE,
    )
    assert len(members) == 1
    assert members[0].license_key == "SCPRO-1111-2222-3333-4444"
    assert members[0].checkout_url == ""


def test_build_cohort_manual_fails_when_key_missing(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\nmissing@example.com,Missing\n", encoding="utf-8")
    keys = tmp_path / "keys.csv"
    keys.write_text(
        "email,license_key,order_id,tier\n"
        "other@example.com,SCPRO-AAAA-BBBB-CCCC-DDDD,beta-phase0-regen-001,admin\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing@example.com"):
        sender._build_cohort(
            cohort, keys, mode="manual", checkout_base=CHECKOUT_BASE,
        )


def test_build_cohort_ls_includes_checkout_url(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\nbuyer@example.com,Buyer\n", encoding="utf-8")
    members = sender._build_cohort(
        cohort, None, mode="ls", checkout_base=CHECKOUT_BASE,
    )
    assert len(members) == 1
    assert members[0].license_key == ""
    assert "buyer%40example.com" in members[0].checkout_url
    assert CHECKOUT_BASE in members[0].checkout_url


def test_render_body_manual_includes_henna_flow_and_license_key() -> None:
    member = sender.CohortMember(
        email="t@example.com",
        name="Tester",
        license_key="SCPRO-AAAA-BBBB-CCCC-DDDD",
    )
    body = sender._render_body(member, henna_base=HENNA, mode="manual")
    assert "BETA_DOWNLOAD/" in body
    assert "BETA_TESTER_QUICKSTART/" in body
    assert "SCPRO-AAAA-BBBB-CCCC-DDDD" in body
    assert HENNA in body
    assert "qClip-Setup-win-x64.exe" in body
    assert "Windows (recommended)" in body
    assert "macOS" in body
    assert "Help menu" in body


def test_render_body_ls_includes_checkout_url() -> None:
    member = sender.CohortMember(
        email="buyer@example.com",
        name="Buyer",
        checkout_url=f"{CHECKOUT_BASE}?checkout%5Bemail%5D=buyer%40example.com",
    )
    body = sender._render_body(member, henna_base=HENNA, mode="ls")
    assert CHECKOUT_BASE in body
    assert "BETA_DOWNLOAD/" in body
    assert "Help menu" in body
    assert "SCPRO-" not in body


def test_main_exits_when_keys_csv_missing(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\nt@example.com,T\n", encoding="utf-8")
    code = sender.main(["--csv", str(cohort), "--keys-csv", str(tmp_path / "missing.csv")])
    assert code == 1
