"""Unit tests for henna GitHub issue filing helpers (no network)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "api" / "support_github.py"


def _load():
    spec = importlib.util.spec_from_file_location("support_github", MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sg = _load()


def test_build_issue_labels_bug_vs_feedback():
    assert sg.build_issue_labels("bug_report") == ["beta", "bug"]
    assert sg.build_issue_labels("beta_feedback") == ["beta", "feedback"]


def test_build_issue_title_truncates_and_prefixes():
    title = sg.build_issue_title(
        {
            "event": "bug_report",
            "severity": "high",
            "categories": ["crash", "gpu"],
        }
    )
    assert title.startswith("[beta] (high)")
    assert "crash" in title

    fb = sg.build_issue_title({"event": "beta_feedback", "severity": "low", "categories": []})
    assert fb.startswith("[beta feedback]")


def test_build_issue_body_includes_job_and_message():
    body = sg.build_issue_body(
        {
            "event": "bug_report",
            "severity": "medium",
            "categories": ["ui"],
            "message": "White screen on launch",
            "job_id": "abc-123",
            "id": "rep-1",
            "device_id": "dev-9",
            "created_at": "2026-08-03T00:00:00Z",
            "environment": {"page": "/jobs"},
        }
    )
    assert "White screen on launch" in body
    assert "`abc-123`" in body
    assert '"page": "/jobs"' in body
    assert "Report a bug" in body


def test_github_project_number_parsing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SUPPORT_GITHUB_PROJECT_NUMBER", raising=False)
    assert sg.github_project_number() == sg.DEFAULT_PROJECT_NUMBER
    monkeypatch.setenv("SUPPORT_GITHUB_PROJECT_NUMBER", "3")
    assert sg.github_project_number() == 3
    monkeypatch.setenv("SUPPORT_GITHUB_PROJECT_NUMBER", "0")
    assert sg.github_project_number() is None
    monkeypatch.setenv("SUPPORT_GITHUB_PROJECT_NUMBER", "nope")
    assert sg.github_project_number() is None
