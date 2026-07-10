"""Build the tester-facing StreamClip beta .zip (attached to invite emails).

No GitHub account or repo access required to use the output — this is the
*only* way testers get the source, since the repo stays private (Option B,
2026-07-09 decision). Uses `git archive` so nothing untracked/gitignored
(secrets, .env, tmp/, dist/, node_modules/, __pycache__, etc.) ever ships.

Usage (repo root):
  python scripts/build_beta_zip.py
  python scripts/build_beta_zip.py --out dist/StreamClip-beta.zip --ref HEAD
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import os
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "dist" / "StreamClip-beta.zip"

# MailScanner and similar scanners flag:
#   - filenames with multiple dots (e.g. docker-compose.prod.yml looks like hidden ext)
#   - common archive extensions (.zip, .tar.gz) as potential malware delivery
# Map source filename → safe name inside the zip to avoid these triggers.
RENAME_INSIDE_ZIP = {
    "docker-compose.prod.yml": "docker-compose-prod.yml",
}

# Keep the tester zip small and free of anything not needed to run
# `docker compose up -d`. Everything here is already git-tracked (git archive
# only includes tracked files), this just trims dev-only tracked content the
# tester doesn't need (CI configs, agent tooling, full test suite).
EXCLUDE_PREFIXES = (
    ".github/",
    ".cursor/",
    ".vscode/",
    "tests/",
    "packaging/",
    "desktop_sidecar/",
    "apps/",
    "web/",       # testers run pre-built Docker images; Next.js source not needed
)
EXCLUDE_FILES = {
    "AGENTS.md",
    "CONTRIBUTING.md",
    "PLAN.md",
    "COMMERCIAL.md",
    "mkdocs.yml",  # internal docs build config, not needed by testers
}


def _tracked_files(ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _should_include(path: str) -> bool:
    if path in EXCLUDE_FILES:
        return False
    return not any(path.startswith(prefix) for prefix in EXCLUDE_PREFIXES)


def build_zip(*, ref: str, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    tracked = _tracked_files(ref)
    included = [p for p in tracked if _should_include(p)]
    excluded_count = len(tracked) - len(included)

    # Build via git archive into a temp buffer, then repack with safe filenames.
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        subprocess.run(
            [
                "git", "archive",
                "--format=zip",
                "--prefix=streamclip/",
                "-o", tmp_path,
                ref,
                "--",
                *included,
            ],
            cwd=REPO_ROOT,
            check=True,
        )

        # Repack: rename any files that trigger mail scanner heuristics.
        with zipfile.ZipFile(tmp_path, "r") as src_zip, \
             zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as dst_zip:
            for item in src_zip.infolist():
                data = src_zip.read(item.filename)
                basename = item.filename.split("/")[-1]
                if basename in RENAME_INSIDE_ZIP:
                    new_name = item.filename[: -len(basename)] + RENAME_INSIDE_ZIP[basename]
                    item.filename = new_name
                dst_zip.writestr(item, data)
    finally:
        os.unlink(tmp_path)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Built {out_path} ({size_mb:.1f} MB, {len(included)} files, {excluded_count} excluded)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the tester beta .zip from tracked git files.")
    parser.add_argument("--ref", default="HEAD", help="Git ref to archive (default: HEAD)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output path (default: {DEFAULT_OUT})")
    args = parser.parse_args(argv)
    return build_zip(ref=args.ref, out_path=args.out)


if __name__ == "__main__":
    raise SystemExit(main())
