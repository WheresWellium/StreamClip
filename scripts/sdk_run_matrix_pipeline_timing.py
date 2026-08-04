#!/usr/bin/env python3
"""Cursor SDK local launcher for the create-option pipeline timing matrix.

Uses a local agent (cwd = repo root) to:
  1) confirm the harness script exists
  2) run / resume scripts/matrix_create_pipeline_timing.py
  3) report green/red from tmp/matrix-pipeline-timing/summary.json

Requires CURSOR_API_KEY. For a no-SDK direct run:
  python scripts/matrix_create_pipeline_timing.py

Usage:
  set CURSOR_API_KEY=...
  python scripts/sdk_run_matrix_pipeline_timing.py
  python scripts/sdk_run_matrix_pipeline_timing.py --limit 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--api-base", default="http://127.0.0.1:8765")
    parser.add_argument("--model", default="composer-2.5")
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "tmp" / "matrix-pipeline-timing"),
    )
    args = parser.parse_args()

    api_key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not api_key:
        print(
            "CURSOR_API_KEY missing. Set it, or run the harness directly:\n"
            "  python scripts/matrix_create_pipeline_timing.py",
            file=sys.stderr,
        )
        return 1

    try:
        from cursor_sdk import Agent, CursorAgentError, LocalAgentOptions
    except ImportError:
        print("cursor-sdk not installed. Run: pip install cursor-sdk", file=sys.stderr)
        return 1

    limit_flag = f" --limit {args.limit}" if args.limit > 0 else ""
    prompt = f"""
You are in the qClip repo at {ROOT}.

Goal: full create-option pipeline wall-clock matrix (9 content profiles x 5 aspects x clip counts 1,5,10,20 = 180 cells).

Do this exactly:
1. Confirm scripts/matrix_create_pipeline_timing.py exists.
2. Confirm API health at {args.api_base}/api/health returns ok (do not start Docker if already healthy).
3. Run:
   python scripts/matrix_create_pipeline_timing.py --api-base {args.api_base} --out-dir {args.out_dir}{limit_flag}
   Use a long block_until / let it finish. The harness is resumable via results.jsonl.
4. Then run with --summarize-only and print summary.json.
5. Final reply MUST include: green true/false, done/failed/missing counts, wall_s_min/mean/max if present.
6. Do not cut a release. Do not edit product code unless the harness itself is broken.
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
            result = run.wait()
            print(flush=True)
            if result.status == "error":
                print(f"run failed: {result.id}", file=sys.stderr)
                return 2
    except CursorAgentError as err:
        print(
            f"startup failed: {err.message} retryable={err.is_retryable}",
            file=sys.stderr,
        )
        return 1

    summary_path = Path(args.out_dir) / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("green") else 2
    print("summary.json missing after agent run", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
