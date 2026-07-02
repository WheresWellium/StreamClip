#!/usr/bin/env python3
"""Benchmark ingest wall time and print Redis timing snapshot."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import get_settings
from core.ingest.service import IngestService
from core.ingest.types import IngestRequest


def _timing_snapshot(job_id: str) -> dict:
    from core.celery_app import get_redis
    from core.progress_timing import _timing_key

    raw = get_redis().get(_timing_key(job_id))
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def run_bench(*, url: str | None, storage_key: str | None, job_id: str) -> None:
    cfg = get_settings()
    svc = IngestService(cfg)

    if url:
        request = IngestRequest(job_id=job_id, source_url=url)
        label = f"URL: {url[:60]}..."
    elif storage_key:
        request = IngestRequest(job_id=job_id, storage_key=storage_key)
        label = f"Upload: {storage_key}"
    else:
        print("Provide --url or --storage-key", file=sys.stderr)
        sys.exit(1)

    print(f"Benchmarking ingest for {label}")
    started = time.perf_counter()

    def on_progress(pct: float) -> None:
        print(f"  progress: {pct:.0%}")

    def on_message(msg: str) -> None:
        print(f"  step: {msg}")

    result = svc.run(request, on_progress=on_progress, on_message=on_message)
    elapsed = time.perf_counter() - started

    print(f"\nDone in {elapsed:.1f}s")
    print(f"  duration: {result.meta.duration:.1f}s")
    print(f"  tier: {result.processing_tier.value}")
    print(f"  size: {result.file_size_bytes or 'n/a'} bytes")

    snap = _timing_snapshot(job_id)
    if snap:
        print(f"  timing snapshot: {json.dumps(snap, indent=2)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark StreamClip ingest")
    parser.add_argument("--url", help="Source URL to download")
    parser.add_argument("--storage-key", help="MinIO storage key for upload ingest")
    parser.add_argument("--job-id", default="bench-ingest", help="Synthetic job id")
    args = parser.parse_args()
    run_bench(url=args.url, storage_key=args.storage_key, job_id=args.job_id)


if __name__ == "__main__":
    main()
