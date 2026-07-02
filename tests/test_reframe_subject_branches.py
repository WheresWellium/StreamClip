from __future__ import annotations
import numpy as np
from unittest.mock import MagicMock
from core.reframe import PRESETS, _SubjectTracker

def test_track_frame_center_drift():
    tr = _SubjectTracker.__new__(_SubjectTracker)
    tr._preset = PRESETS["fps_game"]
    tr._yolo = MagicMock()
    tr._yolo.track.return_value = []
    tr._mp_face = None
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    cx = tr.track_frame(frame, 0.2)
    assert 0.0 <= cx <= 1.0

def test_yolo_picks_center_box():
    tr = _SubjectTracker.__new__(_SubjectTracker)
    tr._preset = PRESETS["fps_game"]
    arr = np.array([[0.1, 0.5, 0.2, 0.2], [0.9, 0.5, 0.2, 0.2]])
    tensor = MagicMock()
    tensor.__len__ = lambda self: len(arr)
    tensor.cpu.return_value.numpy.return_value = arr
    res = MagicMock()
    res.boxes = MagicMock()
    res.boxes.xywhn = tensor
    tr._yolo = MagicMock()
    tr._yolo.track.return_value = [res]
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    cx = tr._yolo_cx(frame)
    assert cx == 0.1
