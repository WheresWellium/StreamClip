"""
Generate qClip desktop icons (app + tray) from one vector-ish definition.

    python scripts/generate_desktop_icons.py

Writes apps/desktop/assets/: icon.png (512), icon.ico (multi-size), tray-icon.png (32).
electron-builder picks up icon.ico from buildResources automatically.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "apps" / "desktop" / "assets"

BG = (10, 15, 28, 255)
ACCENT = (56, 189, 248, 255)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _rounded_bg(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=int(size * 0.22),
        fill=BG,
        outline=ACCENT,
        width=max(1, int(size * 0.035)),
    )
    return img


def _send_mark(size: int) -> list[tuple[float, float]]:
    """Paper-plane / play mark matching the in-app SVG (viewBox 24)."""
    pts = [(2, 21), (23, 12), (2, 3), (2, 10), (17, 12), (2, 14)]
    scale = size / 24.0
    inset = size * 0.20
    span = size - inset * 2
    return [(inset + x * scale * (span / size), inset + y * scale * (span / size)) for x, y in pts]


def render(size: int) -> Image.Image:
    # Supersample for clean edges at small sizes.
    factor = 4
    big = size * factor
    img = _rounded_bg(big)
    ImageDraw.Draw(img).polygon(_send_mark(big), fill=ACCENT)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    icon_png = ASSETS / "icon.png"
    render(512).save(icon_png, format="PNG")

    tray_png = ASSETS / "tray-icon.png"
    render(32).save(tray_png, format="PNG")

    icon_ico = ASSETS / "icon.ico"
    render(256).save(icon_ico, format="ICO", sizes=[(s, s) for s in ICO_SIZES])

    for path in (icon_png, tray_png, icon_ico):
        print(f"{path.relative_to(ROOT)} -> {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
