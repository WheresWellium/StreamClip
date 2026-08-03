"""
GitHub issue filing for henna support-ingest (F13).

Secrets stay on Vercel — desktop never sees the token.
Creates issues on WheresWellium/StreamClip and optionally adds them to a
user Project (Projects v2).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_REPO = "WheresWellium/StreamClip"


def github_token() -> str:
    return (
        os.environ.get("SUPPORT_GITHUB_TOKEN", "").strip()
        or os.environ.get("GITHUB_TOKEN", "").strip()
    )


def github_repo() -> str:
    return os.environ.get("SUPPORT_GITHUB_REPO", DEFAULT_REPO).strip() or DEFAULT_REPO


def github_project_number() -> int | None:
    raw = os.environ.get("SUPPORT_GITHUB_PROJECT_NUMBER", "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if n > 0 else None


def build_issue_labels(event: str) -> list[str]:
    # Labels must exist on the repo (`beta`, `bug`, `feedback`).
    labels = ["beta"]
    if event == "beta_feedback":
        labels.append("feedback")
    else:
        labels.append("bug")
    return labels


def build_issue_title(payload: dict[str, Any]) -> str:
    event = str(payload.get("event") or "support")
    severity = str(payload.get("severity") or "medium")
    categories = payload.get("categories") or []
    if isinstance(categories, list):
        cat_s = ", ".join(str(c) for c in categories if str(c).strip()) or "general"
    else:
        cat_s = str(categories) or "general"
    prefix = "[beta feedback]" if event == "beta_feedback" else "[beta]"
    # GitHub title soft limit ~256; keep readable.
    title = f"{prefix} ({severity}) {cat_s}"
    return title[:240]


def build_issue_body(payload: dict[str, Any]) -> str:
    event = str(payload.get("event") or "support")
    severity = str(payload.get("severity") or "medium")
    message = str(payload.get("message") or "").strip() or "(empty)"
    categories = payload.get("categories") or []
    if isinstance(categories, list):
        cat_s = ", ".join(str(c) for c in categories) or "uncategorized"
    else:
        cat_s = str(categories)

    env = payload.get("environment") or {}
    env_block = json.dumps(env, indent=2, default=str) if env else "{}"

    return "\n".join(
        [
            "Submitted from the qClip desktop app (Help → Report a bug / Beta feedback).",
            "",
            f"**Event:** `{event}`",
            f"**Severity:** `{severity}`",
            f"**Categories:** {cat_s}",
            f"**Job ID:** `{payload.get('job_id') or 'n/a'}`",
            f"**Report ID:** `{payload.get('id') or 'n/a'}`",
            f"**Device ID:** `{payload.get('device_id') or 'n/a'}`",
            f"**Created:** `{payload.get('created_at') or 'n/a'}`",
            "",
            "## Message",
            "",
            message,
            "",
            "## Environment",
            "",
            "```json",
            env_block,
            "```",
            "",
        ]
    )


def _http_json(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    *,
    accept: str = "application/vnd.github+json",
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "qClip-support-ingest/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            body = json.loads(raw) if raw.strip() else {}
            if not isinstance(body, dict):
                body = {"data": body}
            return int(resp.status), body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore") or "{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"message": raw}
        if not isinstance(body, dict):
            body = {"message": str(body)}
        return int(exc.code), body


def create_github_issue(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a repo issue. Returns {ok, number, url, node_id, error?}."""
    token = github_token()
    if not token:
        return {"ok": False, "error": "github_token_unconfigured"}

    repo = github_repo()
    owner, _, name = repo.partition("/")
    if not owner or not name:
        return {"ok": False, "error": "github_repo_invalid"}

    status, body = _http_json(
        "POST",
        f"https://api.github.com/repos/{owner}/{name}/issues",
        token,
        {
            "title": build_issue_title(payload),
            "body": build_issue_body(payload),
            "labels": build_issue_labels(str(payload.get("event") or "bug_report")),
        },
    )
    if status >= 300:
        return {
            "ok": False,
            "error": "github_issue_failed",
            "status": status,
            "detail": body.get("message") or body,
        }
    return {
        "ok": True,
        "number": body.get("number"),
        "url": body.get("html_url"),
        "node_id": body.get("node_id"),
    }


def _graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    status, body = _http_json(
        "POST",
        "https://api.github.com/graphql",
        token,
        {"query": query, "variables": variables},
        accept="application/json",
    )
    if status >= 300:
        return {"ok": False, "error": "graphql_http", "status": status, "detail": body}
    if body.get("errors"):
        return {"ok": False, "error": "graphql_errors", "detail": body["errors"]}
    return {"ok": True, "data": body.get("data") or {}}


def add_issue_to_project(*, issue_node_id: str) -> dict[str, Any]:
    """
    Add an issue to the configured user Project (Projects v2).

    Needs SUPPORT_GITHUB_TOKEN with ``project`` / ``read:project`` scopes and
    SUPPORT_GITHUB_PROJECT_NUMBER (e.g. 1).
    """
    token = github_token()
    number = github_project_number()
    if not token:
        return {"ok": False, "error": "github_token_unconfigured"}
    if number is None:
        return {"ok": False, "error": "project_unconfigured"}
    if not issue_node_id:
        return {"ok": False, "error": "missing_issue_node_id"}

    owner_login = github_repo().split("/", 1)[0]
    # Prefer explicit node id when set (avoids an extra lookup).
    project_id = os.environ.get("SUPPORT_GITHUB_PROJECT_ID", "").strip()
    if not project_id:
        lookup = _graphql(
            token,
            """
            query($login: String!, $number: Int!) {
              user(login: $login) {
                projectV2(number: $number) { id }
              }
            }
            """,
            {"login": owner_login, "number": number},
        )
        if not lookup.get("ok"):
            return lookup
        project_id = (
            ((lookup.get("data") or {}).get("user") or {}).get("projectV2") or {}
        ).get("id") or ""
        if not project_id:
            return {"ok": False, "error": "project_not_found", "number": number}

    add = _graphql(
        token,
        """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item { id }
          }
        }
        """,
        {"projectId": project_id, "contentId": issue_node_id},
    )
    if not add.get("ok"):
        return add
    item_id = (
        ((add.get("data") or {}).get("addProjectV2ItemById") or {}).get("item") or {}
    ).get("id")
    return {"ok": True, "project_id": project_id, "item_id": item_id}


def file_support_to_github(payload: dict[str, Any]) -> dict[str, Any]:
    """Create issue and best-effort project link. Never raises."""
    issue = create_github_issue(payload)
    if not issue.get("ok"):
        return issue
    project = add_issue_to_project(issue_node_id=str(issue.get("node_id") or ""))
    return {
        "ok": True,
        "delivered": "github_issue",
        "issue_number": issue.get("number"),
        "issue_url": issue.get("url"),
        "project": project,
    }
