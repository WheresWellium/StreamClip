"""Send Phase 0 beta test info emails to the cohort (subject: BETA TEST INFO).

Prepares gitignored bodies under dist/phase0-beta-test-info/emails/ and optionally
sends via SMTP (same env vars as core.notify.email).

Usage (repo root):

  # Prepare bodies only (no SMTP required):
  python scripts/send_beta_test_info_emails.py --csv cohort.csv

  # Send when SMTP_* env vars are set (api/worker stack or local .env):
  python scripts/send_beta_test_info_emails.py --csv cohort.csv --send

  # Preview without writing files:
  python scripts/send_beta_test_info_emails.py --csv cohort.csv --dry-run
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.notify.email import send_email, smtp_settings_from_env  # noqa: E402

DEFAULT_SUBJECT = "BETA TEST INFO"
DEFAULT_OUT_DIR = REPO_ROOT / "dist" / "phase0-beta-test-info"

BODY_TEMPLATE = """\
Hi {name},

StreamClip Phase 0 beta — quick reference for testing.

Get started (no GitHub account needed):
https://streamclip-henna.vercel.app/BETA_DOWNLOAD/

Quickstart (~15 min, step-by-step):
https://streamclip-henna.vercel.app/BETA_TESTER_QUICKSTART/

Full test checklist (flows T0-1 through T0-4):
https://streamclip-henna.vercel.app/BETA_TESTER_PLAN/

Known issues and workarounds:
https://streamclip-henna.vercel.app/BETA_KNOWN_ISSUES/

Before your first job, run verify_stack.ps1 (Windows) or follow the quickstart
health check — all checks must be green.

Your license key was in your invite email. Paste it in Settings → License after
logging in (format: SCPRO-…).

Support: use "Beta feedback" or "Report a bug" in the app header. We read every
submission. You can also reply to this email.

Thanks for helping shape launch quality,
Wellium
"""


@dataclass(frozen=True)
class CohortMember:
    email: str
    name: str


def _parse_cohort_csv(path: Path) -> list[CohortMember]:
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        # Fallback: plain email-per-line
        raw = list(csv.reader(io.StringIO(text)))
        start = 1 if raw and raw[0] and raw[0][0].strip().lower() == "email" else 0
        members: list[CohortMember] = []
        for row in raw[start:]:
            if not row:
                continue
            email = row[0].strip()
            if email and "@" in email:
                name = row[1].strip() if len(row) > 1 and row[1].strip() else email.split("@")[0]
                members.append(CohortMember(email=email, name=name))
        return members

    members = []
    for row in rows:
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email or "@" not in email:
            continue
        name = (row.get("name") or row.get("Name") or "").strip()
        if not name:
            name = email.split("@")[0]
        members.append(CohortMember(email=email, name=name))
    return members


def _dedupe(members: list[CohortMember]) -> list[CohortMember]:
    seen: set[str] = set()
    out: list[CohortMember] = []
    for m in members:
        key = m.email.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _safe_filename(email: str) -> str:
    return "".join(c if c.isalnum() or c in "._@-" else "_" for c in email)


def _render_body(member: CohortMember) -> str:
    return BODY_TEMPLATE.format(name=member.name)


def _write_pack(
    members: list[CohortMember],
    *,
    subject: str,
    out_dir: Path,
) -> list[tuple[CohortMember, Path]]:
    emails_dir = out_dir / "emails"
    emails_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[CohortMember, Path]] = []
    index_lines = ["email,name,subject,file"]

    for member in members:
        body = _render_body(member)
        safe = _safe_filename(member.email)
        path = emails_dir / f"{safe}.txt"
        content = f"To: {member.email}\nSubject: {subject}\n\n{body}"
        path.write_text(content, encoding="utf-8")
        written.append((member, path))
        index_lines.append(f"{member.email},{member.name},{subject},emails/{safe}.txt")

    (out_dir / "index.csv").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    checklist = "\n".join(
        [
            "Phase 0 BETA TEST INFO — SEND CHECKLIST",
            f"Subject: {subject}",
            f"Count: {len(members)}",
            "",
            "Send via:",
            "  python scripts/send_beta_test_info_emails.py --csv cohort.csv --send",
            "",
            "Or copy each file under emails/ into your mail client.",
            "Do not commit dist/ (gitignored).",
        ]
    )
    (out_dir / "SEND_CHECKLIST.txt").write_text(checklist + "\n", encoding="utf-8")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send BETA TEST INFO emails to the cohort.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=REPO_ROOT / "cohort.csv",
        help="Cohort CSV with columns email[,name] (default: cohort.csv)",
    )
    parser.add_argument(
        "--subject",
        default=DEFAULT_SUBJECT,
        help=f"Email subject (default: {DEFAULT_SUBJECT})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for prepared bodies",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send via SMTP (requires SMTP_HOST and related env vars)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not write files or send",
    )
    args = parser.parse_args(argv)

    if not args.csv.is_file():
        print(f"Cohort CSV not found: {args.csv}", file=sys.stderr)
        print("Copy cohort.example.csv to cohort.csv and add real emails.", file=sys.stderr)
        return 1

    members = _dedupe(_parse_cohort_csv(args.csv))
    if not members:
        print("No valid emails in cohort CSV.", file=sys.stderr)
        return 1

    subject = args.subject.strip()
    if not subject:
        print("Subject must not be empty.", file=sys.stderr)
        return 1

    if args.dry_run:
        for member in members:
            print(f"DRY-RUN to={member.email} subject={subject!r}")
        print(f"Would prepare/send {len(members)} email(s).", file=sys.stderr)
        return 0

    written = _write_pack(members, subject=subject, out_dir=args.out_dir)
    print(f"Prepared {len(written)} email(s) under {args.out_dir}/emails/", file=sys.stderr)

    if not args.send:
        print("Pass --send to deliver via SMTP.", file=sys.stderr)
        return 0

    smtp = smtp_settings_from_env()
    if not smtp.configured:
        print("SMTP not configured (set SMTP_HOST, etc.). Bodies saved only.", file=sys.stderr)
        return 1

    sent = 0
    failed: list[str] = []
    for member, _path in written:
        body = _render_body(member)
        ok = send_email(to=member.email, subject=subject, body=body, settings=smtp)
        if ok:
            sent += 1
            print(f"SENT {member.email}", file=sys.stderr)
        else:
            failed.append(member.email)
            print(f"FAILED {member.email}", file=sys.stderr)

    print(f"\n{sent}/{len(written)} sent.", file=sys.stderr)
    if failed:
        print("Failed:", ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
