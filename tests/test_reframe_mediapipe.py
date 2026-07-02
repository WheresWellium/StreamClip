from __future__ import annotations
import builtins
import numpy as np
from unittest.mock import MagicMock, patch
from core.reframe import PRESETS, _SubjectTracker

def test_mediapipe_import_error_sets_none():
    ultra = MagicMock()
    ultra.YOLO.return_value = MagicMock()
    real_import = builtins.__import__
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "mediapipe":
            raise ImportError("no mp")
        return real_import(name, globals, locals, fromlist, level)
    with patch.dict("sys.modules", {"ultralytics": ultra}):
        with patch("builtins.__import__", side_effect=fake_import):
            tr = _SubjectTracker(PRESETS["fps_game"])
    assert tr._mp_face is None

def test_mp_cx_with_detection():
    tr = _SubjectTracker.__new__(_SubjectTracker)
    tr._preset = PRESETS["fps_game"]
    mp_face = MagicMock()
    det = MagicMock()
    det.location_data.relative_bounding_box.xmin = 0.25
    det.location_data.relative_bounding_box.width = 0.5
    mp_face.process.return_value = MagicMock(detections=[det])
    tr._mp_face = mp_face
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    with patch("core.reframe.cv2.cvtColor", return_value=frame):
        cx = tr._mp_cx(frame)
    assert cx == 0.5
