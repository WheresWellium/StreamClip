"""Full reframe module coverage with mocks."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from core.config import get_settings
from core.models import ClipCandidate, Emotion, SignalScores
from core import reframe as rf
from core.reframe import PRESETS, _Preset, _smooth_path, _SubjectTracker, create_split_screen

def _cand(emotion=Emotion.HYPE):
    return ClipCandidate(
        segment_id=0, start=0.0, end=3.0, text="x", scores=SignalScores(),
        llm_hook="h", llm_title="t", emotion=emotion,
    )

def test_smooth_path_empty_and_nonempty():
    assert rf._smooth_path([], window=5, max_vel=0.1) == []
    out = _smooth_path([0.5, 0.6, 0.7, 0.8], window=3, max_vel=0.5)
    assert len(out) == 4

def test_resolve_smooth_window():
    p = PRESETS["fps_game"]
    cfg = get_settings(reload=True).reframe
    assert rf._resolve_smooth_window(p, cfg) >= rf.MIN_SMOOTH_WINDOW_FRAMES

def test_subject_tracker_yolo_mp_fallback():
    frame = np.zeros((270, 480, 3), dtype=np.uint8)
    preset = PRESETS["fps_game"]
    box = MagicMock()
    box.cpu.return_value.numpy.return_value = np.array([[0.5, 0.5, 0.2, 0.2]])
    res = MagicMock()
    res.boxes.xywhn = box
    yolo = MagicMock()
    yolo.track.return_value = [res]
    mp_face = MagicMock()
    det = MagicMock()
    det.location_data.relative_bounding_box.xmin = 0.4
    det.location_data.relative_bounding_box.width = 0.2
    mp_face.process.return_value = MagicMock(detections=[det])
    ultra = MagicMock()
    ultra.YOLO.return_value = yolo
    fake_mp = MagicMock()
    fake_mp.solutions.face_detection.FaceDetection.return_value = mp_face
    with patch.dict("sys.modules", {"ultralytics": ultra, "mediapipe": fake_mp}):
        tr = _SubjectTracker(preset)
    assert tr.track_frame(frame, 0.5) == pytest.approx(0.5, abs=0.05)
    res2 = MagicMock()
    res2.boxes = None
    yolo.track.return_value = [res2]
    with patch.dict("sys.modules", {"ultralytics": ultra, "mediapipe": fake_mp}):
        tr2 = _SubjectTracker(preset)
        tr2._mp_face = None
        cx = tr2.track_frame(frame, 0.2)
    assert 0.0 <= cx <= 1.0

def test_reframe_with_tracking_mocked(tmp_path):
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cap = MagicMock()
    cap.get.side_effect = lambda k: {rf.cv2.CAP_PROP_FRAME_WIDTH: 1280, rf.cv2.CAP_PROP_FRAME_HEIGHT: 720,
        rf.cv2.CAP_PROP_FPS: 30.0, rf.cv2.CAP_PROP_FRAME_COUNT: 2}.get(k, 0)
    reads = [(True, frame), (True, frame), (False, None)]
    cap.read.side_effect = reads + reads
    proc = MagicMock()
    with patch.object(rf.cv2, "VideoCapture", return_value=cap):
        with patch.object(rf, "_SubjectTracker") as ST:
            ST.return_value.track_frame.return_value = 0.5
            with patch.object(rf.subprocess, "Popen", return_value=proc):
                with patch.object(rf.cv2, "resize", side_effect=lambda f, s, **kw: np.zeros((s[1], s[0], 3), dtype=np.uint8)):
                    rf._reframe_with_tracking(inp, out, get_settings(reload=True).reframe, PRESETS["fps_game"], get_settings().export)
    proc.stdin.close.assert_called()
    proc.wait.assert_called()

def test_create_split_screen_branches(tmp_path):
    g = tmp_path / "g.mp4"
    w = tmp_path / "w.mp4"
    o = tmp_path / "o.mp4"
    g.write_bytes(b"g")
    w.write_bytes(b"w")
    with patch.object(rf.subprocess, "run") as run:
        create_split_screen(g, w, o)
        create_split_screen(g, None, o)
    assert run.call_count == 2

def test_reframe_split_and_no_fallback_raise(tmp_path):
    cfg = get_settings(reload=True)
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    cam = tmp_path / "cam.mp4"
    inp.write_bytes(b"v")
    cam.write_bytes(b"c")
    with patch.object(rf, "_reframe_with_tracking", return_value=out):
        with patch.object(rf, "create_split_screen", return_value=out):
            rf.reframe(inp, out, cfg, _cand(), webcam_path=cam)
    cfg.reframe.fallback_center_crop = False
    with patch.object(rf, "_reframe_with_tracking", side_effect=RuntimeError("x")):
        with pytest.raises(RuntimeError):
            rf.reframe(inp, out, cfg, _cand(Emotion.NEUTRAL))

def test_reframe_center_crop_fallback_and_auto(tmp_path):
    """Tracking failure uses centre-crop+scale, not letterbox/boxblur."""
    cfg = get_settings(reload=True)
    cfg.reframe.fallback_center_crop = True
    cfg.reframe.preset = "auto"
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"v")
    with patch.object(rf, "_reframe_with_tracking", side_effect=OSError("fail")):
        with patch.object(rf.subprocess, "run") as run:
            rf.reframe(inp, out, cfg, _cand(Emotion.HYPE))
            run.assert_called_once()
            cmd = run.call_args.args[0]
            vf = " ".join(str(x) for x in cmd)
            assert "crop=" in vf
            assert "scale=" in vf
            assert "boxblur" not in vf
            assert "pad=" not in vf
