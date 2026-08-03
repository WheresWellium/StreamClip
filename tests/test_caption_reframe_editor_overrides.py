"""Wave 3 editor overrides: caption hex→ASS colors and reframe pan/zoom."""

from __future__ import annotations

import pytest

from core.captions import hex_to_ass_color
from core.reframe import apply_reframe_zoom, bias_crop_cx


@pytest.mark.parametrize(
    ("hex_color", "ass"),
    [
        ("#FF0000", "&H000000FF"),  # red
        ("#00FF00", "&H0000FF00"),  # green
        ("#0000FF", "&H00FF0000"),  # blue
        ("#FFFFFF", "&H00FFFFFF"),  # white
        ("#000000", "&H00000000"),  # black
        ("#aabbcc", "&H00CCBBAA"),  # mixed case → upper ASS
    ],
)
def test_hex_to_ass_color(hex_color: str, ass: str) -> None:
    assert hex_to_ass_color(hex_color) == ass


def test_hex_to_ass_color_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid hex color"):
        hex_to_ass_color("red")
    with pytest.raises(ValueError, match="Invalid hex color"):
        hex_to_ass_color("#FFF")


def test_bias_crop_cx_pan_left_and_right() -> None:
    # pan_x=0.5 → no bias
    assert bias_crop_cx(0.5, 0.5) == pytest.approx(0.5)
    assert bias_crop_cx(0.7, 0.5) == pytest.approx(0.7)
    # pan left of center shifts tracked center left
    assert bias_crop_cx(0.5, 0.25) == pytest.approx(0.25)
    # pan right of center shifts tracked center right
    assert bias_crop_cx(0.5, 0.75) == pytest.approx(0.75)
    # clamps to [0, 1]
    assert bias_crop_cx(0.9, 0.9) == pytest.approx(1.0)
    assert bias_crop_cx(0.1, 0.1) == pytest.approx(0.0)


def test_apply_reframe_zoom_shrinks_crop() -> None:
    w, h = apply_reframe_zoom(1080, 1920, 1.0)
    assert (w, h) == (1080, 1920)
    w2, h2 = apply_reframe_zoom(1080, 1920, 1.2)
    assert w2 < 1080 and h2 < 1920
    assert w2 == int(1080 / 1.2)
    assert h2 == int(1920 / 1.2)
    # zoom clamps at 1.4
    w3, h3 = apply_reframe_zoom(1000, 1000, 2.0)
    assert (w3, h3) == apply_reframe_zoom(1000, 1000, 1.4)
