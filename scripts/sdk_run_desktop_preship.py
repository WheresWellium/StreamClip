#!/usr/bin/env python3
"""Cursor SDK local launcher for the next desktop ship gates after matrix green.

Runs (via a local agent):
  1) confirm matrix evidence is green (docs/evidence or tmp summary)
  2) scripts/verify_desktop_release.ps1 (unsigned beta path)
  3) print operator-only O4d / O11 residue — do not invent VM results

Requires CURSOR_API_KEY. Direct (no SDK):
  .\\scripts\\verify_desktop_release.ps1

Usage:
  set CURSOR_API_KEY=...
  python scripts/sdk_run_desktop_preship.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="composer-2.5")
    parser.add_argument(
        "--require-signing",
        action="store_true",
        help="Pass -RequireSigning to verify_desktop_release.ps1",
    )
    args = parser.parse_args()

    api_key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not api_key:
        print(
            "CURSOR_API_KEY missing. Set it, or run the gate directly:\n"
            "  .\\scripts\\verify_desktop_release.ps1",
            file=sys.stderr,
        )
        return 1

    try:
        from cursor_sdk import Agent, CursorAgentError, LocalAgentOptions
    except ImportError:
        print("cursor-sdk not installed. Run: pip install cursor-sdk", file=sys.stderr)
        return 1

    signing = " -RequireSigning" if args.require_signing else ""
    prompt = f"""
You are in the qClip repo at {ROOT}.

Context: the 180-cell create-option full pipeline timing matrix is already green
(docs/evidence/matrix-pipeline-timing-beta24.md and/or tmp/matrix-pipeline-timing/summary.json).

Do this exactly:
1. Confirm matrix green (summary.json green true OR evidence file says 180/180).
2. Run: .\\scripts\\verify_desktop_release.ps1{signing}
   Let it finish; do not wrap with Tee-Object.
3. Final reply MUST include: matrix green yes/no, release-gate exit code, and the
   OPERATOR-ONLY leftover lines (clean-VM O4d, EV O11) without inventing Pass/Fail
   for the VM checklist.
4. Do not cut a release. Do not edit product code unless a gate script is broken.
""".strip()

    try:
        with Agent.create(
            model=args.model,
            api_key=api_key,
            local=LocalAgentOptions(cwd=str(ROOT)),
        ) as agent:
            run = agent.send(prompt)
            print(f"agent_id={agent.agent_id} run_id={run.id}", flush=True)
            for message in run.messages():
                if message.type == "assistant":
                    for block in message.message.content:
                        if block.type == "text":
                            print(block.text, end="", flush=True)
            print(flush=True)
            result = run.wait()
            if result.status == "error":
                print(f"run failed: {result.id}", file=sys.stderr)
                return 2
            return 0
    except CursorAgentError as err:
        print(
            f"startup failed: {err.message}, retryable={err.is_retryable}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
