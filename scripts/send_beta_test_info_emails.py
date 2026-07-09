"""Send Phase 0 beta test info emails to the cohort (subject: BETA TEST INFO).

The repo is **private** (Option B, 2026-07-09), so the beta `.zip` built by
``scripts/build_beta_zip.py`` is the *only* way testers get StreamClip — it is
attached directly to this email. No GitHub link, no phantom "repo link in
your invite" promise: the attachment IS the invite.

Uses **existing** license keys from a keys CSV (from ``issue_beta_keys.py`` output).
Does **not** issue or regenerate keys — pass the same ``keys.csv`` / ``tmp/beta-keys.csv``
from the original cohort issuance (e.g. ``beta-phase0-regen-001..005``).

Prepares gitignored bodies under dist/phase0-beta-test-info/emails/ and optionally
sends via SMTP (same env vars as core.notify.email) with the zip attached.

Usage (repo root):

  # Build the attachment first (once per release):
  python scripts/build_beta_zip.py

  # Prepare bodies (requires existing keys CSV — never re-issue keys):
  python scripts/send_beta_test_info_emails.py --csv cohort.csv \\
      --keys-csv dist/phase0-invite-pack/keys.csv

  # Send when SMTP_* env vars are set (attaches dist/StreamClip-beta.zip):
  python scripts/send_beta_test_info_emails.py --csv cohort.csv \\
      --keys-csv tmp/beta-keys.csv --send

  # Preview without writing files:
  python scripts/send_beta_test_info_emails.py --csv cohort.csv \\
      --keys-csv dist/phase0-invite-pack/keys.csv --dry-run
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

HENNA_BASE = "https://streamclip-henna.vercel.app"
DEFAULT_SUBJECT = "BETA TEST INFO"
DEFAULT_OUT_DIR = REPO_ROOT / "dist" / "phase0-beta-test-info"
DEFAULT_ZIP_PATH = REPO_ROOT / "dist" / "StreamClip-beta.zip"
DEFAULT_KEYS_CANDIDATES = (
    REPO_ROOT / "dist" / "phase0-invite-pack" / "keys.csv",
    REPO_ROOT / "tmp" / "beta-keys.csv",
)

# Aligned with docs/index.md tip + BETA_TESTER_QUICKSTART short version.
# The .zip is attached to this email — no GitHub link, no "check your invite
# for a link" circularity. Quickstart/plan/known-issues stay on the public
# henna docs site since those pages carry no source code.
BODY_TEMPLATE = """\
Hi {name},

You're in — welcome to the StreamClip Phase 0 beta.

Getting started (no GitHub account needed):

1. The StreamClip beta files are attached to this email as a .zip.
   Extract it to any folder (e.g. C:\\StreamClip or ~/StreamClip).

2. Quickstart — install to your first clip (~15 min):
   {henna_base}/BETA_TESTER_QUICKSTART/

3. Paste your license key in Settings → License after logging in:
   {license_key}

This key gives you full access to every feature. No feature gates.

The short path:
- Install Docker Desktop (free) and keep it running
- Extract the attached .zip to any folder
- Run the one start command from the quickstart
- Open http://localhost:3000
- Paste a public video link and wait for clips

Use "Beta feedback" or "Report a bug" in the app header for support.
We read every submission even if you don't get an auto-reply yet.

Thanks,
Wellium
"""


@dataclass(frozen=True)
class CohortMember:
    email: str
    name: str
    license_key: str


def _parse_cohort_csv(path: Path) -> list[tuple[str, str]]:
    """Return list of (email, name) without keys."""
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raw = list(csv.reader(io.StringIO(text)))
        start = 1 if raw and raw[0] and raw[0][0].strip().lower() == "email" else 0
        pairs: list[tuple[str, str]] = []
        for row in raw[start:]:
            if not row:
                continue
            email = row[0].strip()
            if email and "@" in email:
                name = row[1].strip() if len(row) > 1 and row[1].strip() else email.split("@")[0]
                pairs.append((email, name))
        return pairs

    pairs = []
    for row in rows:
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email or "@" not in email:
            continue
        name = (row.get("name") or row.get("Name") or "").strip()
        if not name:
            name = email.split("@")[0]
        pairs.append((email, name))
    return pairs


def _parse_keys_csv(path: Path) -> dict[str, str]:
    """Map lowercased email → license_key from issue_beta_keys CSV output."""
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {}
    keys: dict[str, str] = {}
    for row in reader:
        email = (row.get("email") or row.get("Email") or "").strip()
        license_key = (row.get("license_key") or row.get("License_key") or "").strip()
        if email and license_key and "@" in email:
            keys[email.lower()] = license_key
    return keys


def _resolve_keys_csv(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    for candidate in DEFAULT_KEYS_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _build_cohort(
    cohort_path: Path,
    keys_path: Path,
) -> list[CohortMember]:
    key_by_email = _parse_keys_csv(keys_path)
    if not key_by_email:
        raise ValueError(f"No license keys found in {keys_path}")

    members: list[CohortMember] = []
    seen: set[str] = set()
    missing_keys: list[str] = []

    for email, name in _parse_cohort_csv(cohort_path):
        lookup = email.lower()
        if lookup in seen:
            continue
        seen.add(lookup)
        license_key = key_by_email.get(lookup)
        if not license_key:
            missing_keys.append(email)
            continue
        members.append(CohortMember(email=email, name=name, license_key=license_key))

    if missing_keys:
        raise ValueError(
            "Cohort emails missing from keys CSV (do not re-issue — use original keys file): "
            + ", ".join(missing_keys),
        )
    if not members:
        raise ValueError("No cohort members with matching keys.")
    return members


def _safe_filename(email: str) -> str:
    return "".join(c if c.isalnum() or c in "._@-" else "_" for c in email)


def _render_body(member: CohortMember, *, henna_base: str) -> str:
    return BODY_TEMPLATE.format(
        name=member.name,
        license_key=member.license_key,
        henna_base=henna_base.rstrip("/"),
    )


def _write_pack(
    members: list[CohortMember],
    *,
    subject: str,
    out_dir: Path,
    henna_base: str,
) -> list[tuple[CohortMember, Path]]:
    emails_dir = out_dir / "emails"
    emails_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[CohortMember, Path]] = []
    index_lines = ["email,name,license_key,subject,file"]

    for member in members:
        body = _render_body(member, henna_base=henna_base)
        safe = _safe_filename(member.email)
        path = emails_dir / f"{safe}.txt"
        content = f"To: {member.email}\nSubject: {subject}\n\n{body}"
        path.write_text(content, encoding="utf-8")
        written.append((member, path))
        index_lines.append(
            f"{member.email},{member.name},{member.license_key},{subject},emails/{safe}.txt",
        )

    (out_dir / "index.csv").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    checklist = "\n".join(
        [
            "Phase 0 BETA TEST INFO — SEND CHECKLIST",
            f"Subject: {subject}",
            f"Count: {len(members)}",
            "",
            "Keys: reused from existing keys CSV (not re-issued).",
            "",
            "Send via:",
            "  python scripts/send_beta_test_info_emails.py --csv cohort.csv \\",
            "      --keys-csv <same-keys-as-invite> --send",
            "",
            "Or copy each file under emails/ into your mail client.",
            "Do not commit dist/ (gitignored).",
        ],
    )
    (out_dir / "SEND_CHECKLIST.txt").write_text(checklist + "\n", encoding="utf-8")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send BETA TEST INFO emails (existing keys only, henna getting-started flow).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=REPO_ROOT / "cohort.csv",
        help="Cohort CSV with columns email[,name] (default: cohort.csv)",
    )
    parser.add_argument(
        "--keys-csv",
        type=Path,
        default=None,
        help=(
            "Existing keys CSV from issue_beta_keys (email,license_key,...). "
            "Default search: dist/phase0-invite-pack/keys.csv, tmp/beta-keys.csv"
        ),
    )
    parser.add_argument(
        "--subject",
        default=DEFAULT_SUBJECT,
        help=f"Email subject (default: {DEFAULT_SUBJECT})",
    )
    parser.add_argument(
        "--henna-base",
        default=HENNA_BASE,
        help=f"Henna docs base URL (default: {HENNA_BASE})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for prepared bodies",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=DEFAULT_ZIP_PATH,
        help=(
            "Beta .zip to attach (build with scripts/build_beta_zip.py). "
            f"Default: {DEFAULT_ZIP_PATH.relative_to(REPO_ROOT)}"
        ),
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

    keys_path = _resolve_keys_csv(args.keys_csv)
    if keys_path is None:
        print("Keys CSV not found.", file=sys.stderr)
        print(
            "Pass --keys-csv with the original issue_beta_keys output "
            "(dist/phase0-invite-pack/keys.csv or tmp/beta-keys.csv).",
            file=sys.stderr,
        )
        print("Do NOT re-run issue_beta_keys — that would create new keys.", file=sys.stderr)
        return 1

    try:
        members = _build_cohort(args.csv, keys_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    subject = args.subject.strip()
    if not subject:
        print("Subject must not be empty.", file=sys.stderr)
        return 1

    henna_base = args.henna_base.strip().rstrip("/")
    print(f"Using keys from: {keys_path}", file=sys.stderr)

    if args.dry_run:
        for member in members:
            print(
                f"DRY-RUN to={member.email} key={member.license_key[:12]}… subject={subject!r}",
            )
        print(f"Would prepare/send {len(members)} email(s).", file=sys.stderr)
        return 0

    written = _write_pack(
        members,
        subject=subject,
        out_dir=args.out_dir,
        henna_base=henna_base,
    )
    print(f"Prepared {len(written)} email(s) under {args.out_dir}/emails/", file=sys.stderr)

    if not args.send:
        print("Pass --send to deliver via SMTP.", file=sys.stderr)
        return 0

    if not args.zip_path.is_file():
        print(f"Beta zip not found: {args.zip_path}", file=sys.stderr)
        print("Build it first: python scripts/build_beta_zip.py", file=sys.stderr)
        return 1
    zip_mb = args.zip_path.stat().st_size / (1024 * 1024)
    print(f"Attaching {args.zip_path} ({zip_mb:.1f} MB) to every email", file=sys.stderr)

    smtp = smtp_settings_from_env()
    if not smtp.configured:
        print("SMTP not configured (set SMTP_HOST, etc.). Bodies saved only.", file=sys.stderr)
        return 1

    sent = 0
    failed: list[str] = []
    for member, _path in written:
        body = _render_body(member, henna_base=henna_base)
        ok = send_email(
            to=member.email,
            subject=subject,
            body=body,
            settings=smtp,
            attachments=[args.zip_path],
        )
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
