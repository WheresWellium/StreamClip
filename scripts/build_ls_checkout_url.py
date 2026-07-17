#!/usr/bin/env python3
"""Print a Lemon Squeezy checkout URL with optional email/name prefill."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.commerce.checkout_urls import build_ls_checkout_url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build LS checkout URL for invite emails.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL", ""),
        help="Checkout base URL (default: STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL)",
    )
    parser.add_argument("--email", default=None)
    parser.add_argument("--name", default=None)
    args = parser.parse_args(argv)

    try:
        url = build_ls_checkout_url(args.base_url, email=args.email, name=args.name)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
