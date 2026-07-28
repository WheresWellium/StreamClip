#!/usr/bin/env python3
"""Build packaging/cohort/cohort_licenses.json from an operator keys CSV (W2).

Usage (repo root):

  python scripts/build_cohort_seed.py --keys-csv tmp/beta-keys.csv \\
      --out packaging/cohort/cohort_licenses.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.licensing import hash_license_key


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header row in {path}")
        return [dict(row) for row in reader]


def build_seed(keys_csv: Path) -> dict[str, object]:
    licenses: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in _read_rows(keys_csv):
        raw_key = (row.get("license_key") or row.get("key") or "").strip()
        tier = (row.get("tier") or "admin").strip().lower()
        if not raw_key:
            continue
        key_hash = hash_license_key(raw_key)
        if key_hash in seen:
            continue
        seen.add(key_hash)
        licenses.append({"key_hash": key_hash, "tier": tier})
    if not licenses:
        raise ValueError(f"No license_key rows found in {keys_csv}")
    return {"version": 1, "licenses": licenses}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build cohort license hash seed JSON.")
    parser.add_argument("--keys-csv", required=True, type=Path, help="CSV with license_key,tier columns")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "packaging" / "cohort" / "cohort_licenses.json",
        help="Output JSON path (default: packaging/cohort/cohort_licenses.json)",
    )
    args = parser.parse_args(argv)

    if not args.keys_csv.is_file():
        print(f"Keys CSV not found: {args.keys_csv}", file=sys.stderr)
        return 1
    try:
        payload = build_seed(args.keys_csv)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['licenses'])} license hashes to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
