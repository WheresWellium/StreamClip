"""Unit tests for beta key issuance CLI."""

from __future__ import annotations

import pytest

from scripts import issue_beta_keys


def test_issue_beta_keys_dry_run_stdout_csv(capsys: pytest.CaptureFixture[str]) -> None:
    code = issue_beta_keys.main(["--emails", "a@example.com,b@example.com", "--dry-run"])
    assert code == 0
    out = capsys.readouterr()
    assert "email,license_key,order_id" in out.out
    assert "a@example.com" in out.out
    assert "SCPRO-" in out.out
    assert "dry-run" in out.err


def test_issue_beta_keys_requires_input() -> None:
    with pytest.raises(SystemExit):
        issue_beta_keys.main([])


def test_parse_emails_csv_skips_header(tmp_path) -> None:
    path = tmp_path / "cohort.csv"
    path.write_text("email\ntester@example.com\n", encoding="utf-8")
    emails = issue_beta_keys._parse_emails_csv(path)
    assert emails == ["tester@example.com"]
