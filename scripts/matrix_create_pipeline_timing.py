#!/usr/bin/env python3
"""Full create-option matrix: wall-clock pipeline timing per cell.

Matrix = content_profile x aspect_ratio x target_clips {1,5,10,20} = 180 cells.
Each cell: upload fixture -> POST /api/jobs -> poll until done|error.
Results append to a JSONL checkpoint so runs can resume.

Usage:
  python scripts/matrix_create_pipeline_timing.py
  python scripts/matrix_create_pipeline_timing.py --api-base http://127.0.0.1:8765 --limit 3
  python scripts/matrix_create_pipeline_timing.py --resume tmp/matrix-pipeline-timing/results.jsonl

Green = every scheduled cell status=done with wall_s recorded.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tmp" / "fixtures" / "smoke_video.mp4"
CLIP_COUNTS = (1, 5, 10, 20)


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | bytes | None = None,
    timeout: float = 60,
) -> Any:
    hdrs = dict(headers or {})
    data: bytes | None = None
    if isinstance(body, dict):
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif isinstance(body, (bytes, bytearray)):
        data = bytes(body)
    req = Request(url, data=data, headers=hdrs, method=method)
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def http_put_file(url: str, path: Path, content_type: str, timeout: float = 120) -> None:
    data = path.read_bytes()
    req = Request(
        url,
        data=data,
        headers={"Content-Type": content_type},
        method="PUT",
    )
    with urlopen(req, timeout=timeout) as resp:
        resp.read()


def load_done_keys(results_path: Path) -> set[str]:
    done: set[str] = set()
    if not results_path.is_file():
        return done
    for line in results_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = row.get("cell_key")
        if key and row.get("status") in {"done", "error", "timeout", "fail"}:
            # Only skip successful dones on resume; retry failures unless --skip-failed
            if row.get("status") == "done":
                done.add(str(key))
    return done


def append_result(results_path: Path, row: dict[str, Any]) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def cell_key(profile: str, aspect: str, clips: int) -> str:
    return f"{profile}|{aspect}|c{clips}"


def build_matrix(meta: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = meta.get("content_profiles") or []
    aspects = [a["id"] for a in (meta.get("aspect_ratios") or [])]
    cells: list[dict[str, Any]] = []
    for p in profiles:
        pid = p["id"]
        for aspect in aspects:
            for clips in CLIP_COUNTS:
                cells.append(
                    {
                        "cell_key": cell_key(pid, aspect, clips),
                        "content_profile": pid,
                        "aspect_ratio": aspect,
                        "target_clips": clips,
                        "reframe_preset": p.get("recommended_reframe") or "auto",
                        "caption_style": p.get("recommended_captions") or "none",
                    }
                )
    return cells


def run_cell(
    *,
    api_base: str,
    headers: dict[str, str],
    fixture: Path,
    cell: dict[str, Any],
    timeout_s: int,
    poll_s: float,
) -> dict[str, Any]:
    key = cell["cell_key"]
    t0 = time.perf_counter()
    row: dict[str, Any] = {
        "cell_key": key,
        "content_profile": cell["content_profile"],
        "aspect_ratio": cell["aspect_ratio"],
        "target_clips": cell["target_clips"],
        "reframe_preset": cell["reframe_preset"],
        "caption_style": cell["caption_style"],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        bytes_len = fixture.stat().st_size
        init = http_json(
            "POST",
            f"{api_base}/api/uploads/init",
            headers=headers,
            body={
                "filename": f"matrix-{key.replace('|', '-')}.mp4",
                "content_type": "video/mp4",
                "size_bytes": bytes_len,
            },
        )
        put_url = init["upload_url"]
        if put_url.startswith("/"):
            put_url = f"{api_base}{put_url}"
        http_put_file(put_url, fixture, "video/mp4")

        job = http_json(
            "POST",
            f"{api_base}/api/jobs",
            headers=headers,
            body={
                "source_upload_key": init["storage_key"],
                "display_title": f"matrix {key}",
                "target_clips": cell["target_clips"],
                "aspect_ratio": cell["aspect_ratio"],
                "reframe_preset": cell["reframe_preset"],
                "caption_style": cell["caption_style"],
                "content_profile": cell["content_profile"],
            },
        )
        job_id = job["id"]
        row["job_id"] = job_id

        deadline = time.time() + timeout_s
        last_status = ""
        while time.time() < deadline:
            time.sleep(poll_s)
            j = http_json("GET", f"{api_base}/api/jobs/{job_id}", headers=headers)
            status = j.get("status") or ""
            stage = j.get("current_stage") or ""
            progress = j.get("progress")
            marker = f"{status}/{stage}/{progress}"
            if marker != last_status:
                print(f"  [{key}] {marker}", flush=True)
                last_status = marker
            if status in {"error", "failed", "cancelled"}:
                row["status"] = "error"
                row["error_code"] = j.get("error_code")
                row["error_message"] = j.get("error_message")
                row["wall_s"] = round(time.perf_counter() - t0, 2)
                row["clip_count"] = len(j.get("clips") or [])
                return row
            if status in {"done", "completed"}:
                row["status"] = "done"
                row["wall_s"] = round(time.perf_counter() - t0, 2)
                row["clip_count"] = len(j.get("clips") or [])
                row["final_stage"] = stage
                return row

        row["status"] = "timeout"
        row["wall_s"] = round(time.perf_counter() - t0, 2)
        row["last"] = last_status
        return row
    except (HTTPError, URLError, KeyError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        row["status"] = "fail"
        row["error_message"] = str(exc)
        row["wall_s"] = round(time.perf_counter() - t0, 2)
        return row


def summarize(results_path: Path, expected_keys: list[str]) -> dict[str, Any]:
    by_key: dict[str, dict[str, Any]] = {}
    if results_path.is_file():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = row.get("cell_key")
            if k:
                by_key[str(k)] = row
    done = [by_key[k] for k in expected_keys if by_key.get(k, {}).get("status") == "done"]
    failed = [
        by_key[k]
        for k in expected_keys
        if by_key.get(k) and by_key[k].get("status") != "done"
    ]
    missing = [k for k in expected_keys if k not in by_key]
    walls = [float(r["wall_s"]) for r in done if isinstance(r.get("wall_s"), (int, float))]
    summary = {
        "expected": len(expected_keys),
        "done": len(done),
        "failed": len(failed),
        "missing": len(missing),
        "green": len(done) == len(expected_keys) and not missing,
        "wall_s_min": min(walls) if walls else None,
        "wall_s_max": max(walls) if walls else None,
        "wall_s_mean": round(sum(walls) / len(walls), 2) if walls else None,
        "failed_keys": [r.get("cell_key") for r in failed[:20]],
        "missing_keys": missing[:20],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8765")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "tmp" / "matrix-pipeline-timing",
    )
    parser.add_argument("--timeout-minutes", type=int, default=25)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--limit", type=int, default=0, help="Max new cells this invocation")
    parser.add_argument("--device-id", default="")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    out_dir: Path = args.out_dir
    results_path = out_dir / "results.jsonl"
    summary_path = out_dir / "summary.json"

    if not args.fixture.is_file():
        print(f"FAIL fixture missing: {args.fixture}", file=sys.stderr)
        return 1

    device_id = args.device_id or f"matrix-{uuid.uuid4().hex[:12]}"
    headers = {"X-Device-Id": device_id, "Content-Type": "application/json"}

    try:
        http_json(
            "POST",
            f"{api_base}/api/devices/onboarding-complete",
            headers=headers,
            body={"device_id": device_id},
        )
    except Exception:
        pass

    meta = http_json("GET", f"{api_base}/api/meta", headers=headers)
    cells = build_matrix(meta)
    expected_keys = [c["cell_key"] for c in cells]
    print(f"matrix cells={len(cells)} api={api_base} fixture={args.fixture}", flush=True)

    if args.summarize_only:
        summary = summarize(results_path, expected_keys)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0 if summary["green"] else 2

    already = load_done_keys(results_path)
    pending = [c for c in cells if c["cell_key"] not in already]
    print(f"resume: done={len(already)} pending={len(pending)}", flush=True)
    if args.limit > 0:
        pending = pending[: args.limit]
        print(f"limit this run to {len(pending)} cells", flush=True)

    timeout_s = max(60, args.timeout_minutes * 60)
    for idx, cell in enumerate(pending, 1):
        print(f"[{idx}/{len(pending)}] START {cell['cell_key']}", flush=True)
        row = run_cell(
            api_base=api_base,
            headers=headers,
            fixture=args.fixture,
            cell=cell,
            timeout_s=timeout_s,
            poll_s=args.poll_seconds,
        )
        append_result(results_path, row)
        print(
            f"[{idx}/{len(pending)}] {row['status']} {cell['cell_key']} "
            f"wall_s={row.get('wall_s')} job={row.get('job_id')}",
            flush=True,
        )

    summary = summarize(results_path, expected_keys)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary["green"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
