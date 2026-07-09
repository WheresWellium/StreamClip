"""Unit tests for BETA TEST INFO email script (keys reuse + henna flow)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import send_beta_test_info_emails as sender


def test_parse_keys_csv_maps_email_to_key(tmp_path: Path) -> None:
    path = tmp_path / "keys.csv"
    path.write_text(
        "email,license_key,order_id,tier\n"
        "a@example.com,SCPRO-AAAA-BBBB-CCCC-DDDD,beta-phase0-regen-001,admin\n",
        encoding="utf-8",
    )
    keys = sender._parse_keys_csv(path)
    assert keys["a@example.com"] == "SCPRO-AAAA-BBBB-CCCC-DDDD"


def test_build_cohort_requires_existing_keys(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\ntester@example.com,Tester\n", encoding="utf-8")
    keys = tmp_path / "keys.csv"
    keys.write_text(
        "email,license_key,order_id,tier\n"
        "tester@example.com,SCPRO-1111-2222-3333-4444,beta-phase0-regen-001,admin\n",
        encoding="utf-8",
    )
    members = sender._build_cohort(cohort, keys)
    assert len(members) == 1
    assert members[0].license_key == "SCPRO-1111-2222-3333-4444"


def test_build_cohort_fails_when_key_missing(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\nmissing@example.com,Missing\n", encoding="utf-8")
    keys = tmp_path / "keys.csv"
    keys.write_text(
        "email,license_key,order_id,tier\n"
        "other@example.com,SCPRO-AAAA-BBBB-CCCC-DDDD,beta-phase0-regen-001,admin\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing@example.com"):
        sender._build_cohort(cohort, keys)


def test_render_body_includes_attached_zip_flow_and_license_key() -> None:
    member = sender.CohortMember(
        email="t@example.com",
        name="Tester",
        license_key="SCPRO-AAAA-BBBB-CCCC-DDDD",
    )
    body = sender._render_body(member, henna_base="https://streamclip-henna.vercel.app")
    assert "attached" in body
    assert "BETA_TESTER_QUICKSTART/" in body
    assert "SCPRO-AAAA-BBBB-CCCC-DDDD" in body
    assert "http://localhost:3000" in body
    assert "Docker Desktop" in body
    # No GitHub links — repo stays private (Option B, 2026-07-09).
    assert "github.com" not in body.lower()


def test_main_exits_when_keys_csv_missing(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\nt@example.com,T\n", encoding="utf-8")
    code = sender.main(["--csv", str(cohort), "--keys-csv", str(tmp_path / "missing.csv")])
    assert code == 1


def test_main_exits_when_send_requested_but_zip_missing(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("email,name\nt@example.com,T\n", encoding="utf-8")
    keys = tmp_path / "keys.csv"
    keys.write_text(
        "email,license_key,order_id,tier\nt@example.com,SCPRO-AAAA-BBBB-CCCC-DDDD,order-1,admin\n",
        encoding="utf-8",
    )
    code = sender.main(
        [
            "--csv", str(cohort),
            "--keys-csv", str(keys),
            "--out-dir", str(tmp_path / "out"),
            "--zip-path", str(tmp_path / "nonexistent.zip"),
            "--send",
        ],
    )
    assert code == 1
