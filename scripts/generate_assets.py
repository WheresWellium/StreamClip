"""Generate minimal placeholder assets without ffmpeg (stdlib only)."""

from __future__ import annotations

import json
import os
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(os.environ.get("STREAMCLIP_ASSETS_DIR", str(ROOT / "assets")))

MANIFEST = [
    {"path": "gifs/hype.gif", "type": "gif", "description": "absolute hype, let's go, incredible win, amazing play, fire moment, clutch victory", "sfx": "sfx/airhorn.mp3", "duration": 2.5, "tags": ["hype", "win", "clutch", "fire"]},
    {"path": "gifs/holy_shit.gif", "type": "gif", "description": "disbelief, unbelievable, cannot believe, shocked, mind blown, what just happened", "sfx": "sfx/vine_boom.mp3", "duration": 2.0, "tags": ["holy", "shocked", "disbelief"]},
    {"path": "gifs/fail.gif", "type": "gif", "description": "epic fail, I died, we lost, terrible mistake, that was awful, RIP", "sfx": "sfx/sad_trombone.mp3", "duration": 2.0, "tags": ["fail", "dead", "rip", "loss"]},
    {"path": "gifs/rage.gif", "type": "gif", "description": "rage, anger, furious, tilted, malding, so frustrated, this game is broken", "sfx": None, "duration": 2.5, "tags": ["rage", "angry", "tilted"]},
    {"path": "gifs/lul.gif", "type": "gif", "description": "laughing, that's hilarious, so funny, comedy, unexpected, absurd", "sfx": "sfx/laugh.mp3", "duration": 2.0, "tags": ["funny", "laugh", "lul"]},
    {"path": "stickers/skull.png", "type": "png", "description": "died, eliminated, got killed, took damage, lost a life", "sfx": "sfx/vine_boom.mp3", "duration": 1.5, "tags": ["death", "eliminated"]},
    {"path": "stickers/fire.png", "type": "png", "description": "on fire, insane streak, hot, dominating, unstoppable", "sfx": None, "duration": 2.0, "tags": ["fire", "streak", "insane"]},
    {"path": "stickers/gg.png", "type": "png", "description": "good game, respect, sportsmanship, handshake, well played", "sfx": "sfx/applause.mp3", "duration": 1.5, "tags": ["gg", "respect"]},
]

SFX_FILES = ["airhorn.mp3", "vine_boom.mp3", "sad_trombone.mp3", "laugh.mp3", "applause.mp3", "whoosh.mp3", "ding.mp3", "record_scratch.mp3"]

# Minimal 1x1 transparent GIF89a
MINI_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
    b"\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _mini_png(r: int, g: int, b: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00" + bytes([r, g, b])
    idat = zlib.compress(raw)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _mini_mp3() -> bytes:
    # Minimal valid-ish MPEG frame header (silence stub for overlay SFX slot)
    return b"\xff\xfb\x90\x00" + b"\x00" * 128


def main() -> int:
    colors = [(255, 80, 80), (255, 160, 0), (255, 220, 0), (180, 80, 255), (0, 200, 200)]
    for i, item in enumerate(MANIFEST):
        path = ASSETS / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if item["type"] == "gif":
            path.write_bytes(MINI_GIF)
        else:
            c = colors[i % len(colors)]
            path.write_bytes(_mini_png(*c))

    for name in SFX_FILES:
        p = ASSETS / "sfx" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_mini_mp3())

    (ASSETS / "manifest.json").write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
    print(f"Generated assets in {ASSETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
