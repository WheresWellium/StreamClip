"""End-to-end API smoke test for StreamClip."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://localhost:8000"
VIDEO = Path("/app/workspace/test.mp4")


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    if not VIDEO.exists():
        print(f"Missing video: {VIDEO}", file=sys.stderr)
        return 1

    init = _post("/api/uploads/init", {
        "filename": "test.mp4",
        "content_type": "video/mp4",
    })
    print("upload init", init["storage_key"])

    put_url = init["upload_url"].replace("localhost:9000", "minio:9000")
    put_req = urllib.request.Request(
        put_url,
        data=VIDEO.read_bytes(),
        method="PUT",
        headers={"Content-Type": "video/mp4"},
    )
    with urllib.request.urlopen(put_req, timeout=120):
        pass
    print("uploaded")

    job = _post("/api/jobs", {
        "source_upload_key": init["storage_key"],
        "target_clips": 2,
        "caption_style": "gaming_impact",
        "reframe_preset": "fps_game",
        "min_virality_score": 40,
    })
    job_id = job["id"]
    print("job", job_id, job["status"])

    for i in range(180):
        j = _get(f"/api/jobs/{job_id}")
        clips = len(j.get("clips", []))
        print(
            f"poll {i}: {j['status']} {j['progress']:.2f} "
            f"{j['current_stage']} clips={clips}",
        )
        if j["status"] == "done":
            for c in j.get("clips", []):
                print(
                    f"  clip {c['rank']}: {c['title']} "
                    f"download={bool(c.get('download_url'))}",
                )
            return 0
        if j["status"] == "error":
            print("error:", j.get("error_message"), j.get("error_code"))
            return 1
        time.sleep(10)

    print("timeout")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
