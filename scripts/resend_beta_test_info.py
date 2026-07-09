"""Send BETA TEST INFO emails via Resend API (no SMTP setup needed).

Reads cohort + keys CSV, sends one email per tester.
Falls back to override_to when domain is not yet verified on Resend.

Usage:
  python scripts/resend_beta_test_info.py --api-key <key> --from <addr>
  python scripts/resend_beta_test_info.py --api-key <key> --from <addr> --override-to you@example.com
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

HENNA_BASE = "https://streamclip-henna.vercel.app"
SUBJECT = "BETA TEST INFO"

DEFAULT_KEYS_CANDIDATES = (
    REPO_ROOT / "dist" / "phase0-invite-pack" / "keys.csv",
    REPO_ROOT / "tmp" / "beta-keys.csv",
)

BODY_TEMPLATE = """\
Hi {name},

You're in — welcome to the StreamClip Phase 0 beta.

Getting started (no GitHub account needed):

1. Download and install:
   {henna_base}/BETA_DOWNLOAD/

   Windows (no Docker): direct download link —
   https://github.com/WheresWellium/StreamClip/releases/download/v1.0.0-beta.2/StreamClip-Setup-win-x64.exe
   Windows may show "Windows protected your PC" — click More info → Run anyway. That's normal for an unsigned beta.

   Mac: use Docker (the .dmg installer is not ready yet — do NOT run any .sh scripts)
   Follow the macOS tab on the download page above.

2. Quickstart — step by step (~15 min):
   {henna_base}/BETA_TESTER_QUICKSTART/

3. Paste your license key in Settings → License after logging in:
   {license_key}

This key gives you full access to every feature. No feature gates.

The short path (Docker, Windows or Mac):
- Install Docker Desktop (free) and keep it running
- Extract the beta .zip from your invite email to any folder
- Open a terminal in that folder and run the start command from the quickstart
- Open http://localhost:3000
- Paste a public video link and wait for clips

Use "Beta feedback" or "Report a bug" in the app header for support.
We read every submission even if you don't get an auto-reply yet.

Thanks,
Wellium
"""


@dataclass(frozen=True)
class Tester:
    email: str
    name: str
    license_key: str


def _parse_keys_csv(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    out: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(text)):
        email = (row.get("email") or "").strip()
        key = (row.get("license_key") or "").strip()
        if email and key:
            out[email.lower()] = key
    return out


def _parse_cohort(path: Path, keys: dict[str, str]) -> list[Tester]:
    text = path.read_text(encoding="utf-8-sig")
    testers: list[Tester] = []
    seen: set[str] = set()
    missing: list[str] = []
    for row in csv.DictReader(io.StringIO(text)):
        email = (row.get("email") or "").strip()
        if not email or "@" not in email:
            continue
        lo = email.lower()
        if lo in seen:
            continue
        seen.add(lo)
        name = (row.get("name") or email.split("@")[0]).strip()
        key = keys.get(lo)
        if not key:
            missing.append(email)
            continue
        testers.append(Tester(email=email, name=name, license_key=key))
    if missing:
        print(f"WARN: no key found for: {', '.join(missing)}", file=sys.stderr)
    return testers


def _send_one(*, api_key: str, from_addr: str, to: str, subject: str, text: str) -> dict:
    payload = json.dumps({"from": from_addr, "to": [to], "subject": subject, "text": text})
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST", "https://api.resend.com/emails",
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stdout or result.stderr}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send BETA TEST INFO via Resend.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--from", dest="from_addr", default="onboarding@resend.dev")
    parser.add_argument("--csv", type=Path, default=REPO_ROOT / "cohort.csv")
    parser.add_argument("--keys-csv", type=Path, default=None)
    parser.add_argument(
        "--override-to",
        default=None,
        help="Send all emails to this address instead (use until domain is verified)",
    )
    args = parser.parse_args(argv)

    keys_path = args.keys_csv
    if keys_path is None:
        for c in DEFAULT_KEYS_CANDIDATES:
            if c.is_file():
                keys_path = c
                break
    if keys_path is None or not keys_path.is_file():
        print("Keys CSV not found. Pass --keys-csv.", file=sys.stderr)
        return 1

    print(f"Keys: {keys_path}", file=sys.stderr)
    keys = _parse_keys_csv(keys_path)
    if not keys:
        print("No keys parsed from CSV.", file=sys.stderr)
        return 1

    if not args.csv.is_file():
        print(f"Cohort CSV not found: {args.csv}", file=sys.stderr)
        return 1

    testers = _parse_cohort(args.csv, keys)
    if not testers:
        print("No testers to send to.", file=sys.stderr)
        return 1

    sent = 0
    failed: list[str] = []
    for tester in testers:
        body = BODY_TEMPLATE.format(
            name=tester.name,
            license_key=tester.license_key,
            henna_base=HENNA_BASE,
        )
        deliver_to = args.override_to or tester.email
        label = f"{tester.email}" + (f" → {deliver_to}" if args.override_to else "")
        print(f"Sending to {label} ...", file=sys.stderr)
        result = _send_one(
            api_key=args.api_key,
            from_addr=args.from_addr,
            to=deliver_to,
            subject=SUBJECT,
            text=body,
        )
        if "id" in result:
            print(f"  OK  id={result['id']}", file=sys.stderr)
            sent += 1
        else:
            print(f"  FAIL  {result}", file=sys.stderr)
            failed.append(tester.email)
        time.sleep(0.4)  # stay well under Resend rate limit

    print(f"\n{sent}/{len(testers)} sent.", file=sys.stderr)
    if failed:
        print("Failed:", ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
