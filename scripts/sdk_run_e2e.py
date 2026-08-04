#!/usr/bin/env python3
"""Cursor SDK local launcher for the full Playwright e2e suite.

Runs (via a local agent):
  1) npm run test:e2e:ui-journey  (mock API — create→review→failure paths)
  2) live happy-path with E2E_RUN=1 against API_BASE (default desktop sidecar :8765)
     + Next.js on :3000 with API_INTERNAL_URL pointed at that API

Requires CURSOR_API_KEY. Direct (no SDK):
  .\\scripts\\run_e2e_full.ps1

Usage:
  set CURSOR_API_KEY=...
  python scripts/sdk_run_e2e.py
  python scripts/sdk_run_e2e.py --api-base http://127.0.0.1:8765
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
    parser.add_argument("--api-base", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="Only run mock ui-journey (no Next + happy-path)",
    )
    args = parser.parse_args()

    api_key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not api_key:
        print(
            "CURSOR_API_KEY missing. Set it, or run directly:\n"
            "  .\\scripts\\run_e2e_full.ps1",
            file=sys.stderr,
        )
        return 1

    try:
        from cursor_sdk import Agent, CursorAgentError, LocalAgentOptions
    except ImportError:
        print("cursor-sdk not installed. Run: pip install cursor-sdk", file=sys.stderr)
        return 1

    skip = " -SkipLive" if args.skip_live else ""
    prompt = f"""
You are in the qClip repo at {ROOT}.

Goal: full Playwright e2e (next highest automatable gate after matrix green).

Do this exactly:
1. Run: .\\scripts\\run_e2e_full.ps1 -ApiBase {args.api_base}{skip}
   Do not wrap with Tee-Object. Let it finish.
2. Final reply MUST include: ui-journey pass/fail counts, live happy-path
   pass/fail (or skipped), and overall green true/false.
3. Do not cut a release. Do not invent clean-VM (O4d) results.
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
