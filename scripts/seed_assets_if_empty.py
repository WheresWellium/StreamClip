"""Seed bundled overlay assets into an empty volume (production Docker)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ASSETS_DIR = Path(os.environ.get("STREAMCLIP_ASSETS_DIR", "/app/assets"))
MANIFEST = ASSETS_DIR / "manifest.json"


def main() -> int:
    if MANIFEST.is_file():
        return 0
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve().parent / "generate_assets.py"
    env = {**os.environ, "STREAMCLIP_ASSETS_DIR": str(ASSETS_DIR)}
    subprocess.run([sys.executable, str(script)], check=True, env=env)
    print(f"Seeded default assets at {ASSETS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
