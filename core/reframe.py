"""
StreamClip — Reframe Engine
Converts source clips to the configured export aspect ratio (9:16 vertical by
default; also 1:1, 4:5, 16:9, 2:3) using YOLOv11 + ByteTrack subject tracking
with a smooth virtual camera path.

Gaming-specific enhancements:
  • HUD protection zones (health bars, minimap, kill feed)
  • Per-genre presets (fps_game, moba, battle_royale, irl, podcast)
  • Split-screen mode: gameplay top / facecam bottom (if cam feed supplied)
  • Letterbox fallback with blurred background (no ugly black bars)
  • Frame-accurate scene-change-aware reframing via PySceneDetect
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import structlog

from core.config import Settings, ReframeConfig, ExportConfig, get_settings
from core.export_video import audio_encode_args, output_fps_args, video_encode_args
from core.ffmpeg_bins import ffmpeg_bin, ffprobe_bin
from core.models import ClipCandidate

log = structlog.get_logger(__name__)

# Camera path smoothing never goes below this many frames (preset-independent floor).
MIN_SMOOTH_WINDOW_FRAMES = 60


def _resolve_smooth_window(preset: _Preset, cfg: ReframeConfig) -> int:
    """Pick smoothing window — always at least MIN_SMOOTH_WINDOW_FRAMES."""
    return max(MIN_SMOOTH_WINDOW_FRAMES, preset.smooth_window, cfg.smooth_window_frames)


# ─── Preset definitions ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _Preset:
    yolo_conf: float          # detection confidence threshold
    track_classes: list[int]  # COCO class IDs to track (0=person, 2=car…)
    smooth_window: int        # camera smoothing window (frames)
    max_pan_velocity: float   # max pan speed (fraction of width per frame)
    hud_bottom: float         # reserve at bottom for health/ammo HUDs
    hud_top: float            # reserve at top for kill feed


PRESETS: dict[str, _Preset] = {
    # FPS: facecam + crosshair focus, fast action, HUD protection critical
    "fps_game": _Preset(
        yolo_conf=0.45, track_classes=[0], smooth_window=60,
        max_pan_velocity=0.06, hud_bottom=0.18, hud_top=0.10,
    ),
    # MOBA: slower camera, wider scene, protect minimap (usually bottom-right)
    "moba": _Preset(
        yolo_conf=0.40, track_classes=[0], smooth_window=60,
        max_pan_velocity=0.03, hud_bottom=0.22, hud_top=0.08,
    ),
    # Battle Royale: follows player aggressively, fast pans OK
    "battle_royale": _Preset(
        yolo_conf=0.45, track_classes=[0], smooth_window=60,
        max_pan_velocity=0.08, hud_bottom=0.15, hud_top=0.08,
    ),
    # IRL/Podcast: talking head — tight face crop, minimal pan
    "irl": _Preset(
        yolo_conf=0.50, track_classes=[0], smooth_window=90,
        max_pan_velocity=0.02, hud_bottom=0.0, hud_top=0.0,
    ),
    "podcast": _Preset(
        yolo_conf=0.50, track_classes=[0], smooth_window=90,
        max_pan_velocity=0.01, hud_bottom=0.0, hud_top=0.0,
    ),
    # Sports: follows athletes, moderate-fast pans, no HUD reserves
    "sports_action": _Preset(
        yolo_conf=0.48, track_classes=[0], smooth_window=70,
        max_pan_velocity=0.07, hud_bottom=0.0, hud_top=0.0,
    ),
    # Webinars / slides: minimal movement, center-weighted
    "presentation": _Preset(
        yolo_conf=0.35, track_classes=[0], smooth_window=120,
        max_pan_velocity=0.008, hud_bottom=0.0, hud_top=0.0,
    ),
    # Scenic B-roll: very slow, gentle pans
    "cinematic_wide": _Preset(
        yolo_conf=0.38, track_classes=[0], smooth_window=150,
        max_pan_velocity=0.015, hud_bottom=0.0, hud_top=0.0,
    ),
    # Music / stage: center-weighted performer tracking, moderate motion
    "music_performance": _Preset(
        yolo_conf=0.42, track_classes=[0], smooth_window=100,
        max_pan_velocity=0.025, hud_bottom=0.0, hud_top=0.0,
    ),
}


# ─── Camera path smoother ─────────────────────────────────────────────────────

def _smooth_path(
    raw_cx: list[float],  # raw centre-x per frame (normalised 0–1)
    window: int,
    max_vel: float,
) -> list[float]:
    """
    Two-pass smoothing:
      Pass 1 — Gaussian blur to remove jitter.
      Pass 2 — Velocity clamp to prevent whip-pans.
    """
    if not raw_cx:
        return raw_cx

    arr = np.array(raw_cx)

    # Gaussian smoothing
    kernel_size = max(3, window | 1)  # must be odd
    sigma = window / 6.0
    smoothed = cv2.GaussianBlur(arr.reshape(1, -1), (kernel_size, 1), sigma)
    smoothed = smoothed.reshape(-1)

    # Velocity clamp
    clamped = [smoothed[0]]
    for v in smoothed[1:]:
        delta = v - clamped[-1]
        delta = np.clip(delta, -max_vel, max_vel)
        clamped.append(clamped[-1] + delta)

    return [float(v) for v in clamped]


# ─── Subject detector ─────────────────────────────────────────────────────────

class _SubjectTracker:
    """
    YOLO + ByteTrack-based subject tracker.
    Falls back to MediaPipe face detection if YOLO finds nothing.
    Falls back to centre of frame as last resort.
    """

    def __init__(self, preset: _Preset) -> None:
        from ultralytics import YOLO
        self._yolo = YOLO("yolo11n.pt")   # auto-downloaded on first run
        self._preset = preset
        try:
            import mediapipe as mp
            self._mp_face = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.5
            )
        except ImportError:
            self._mp_face = None

    def _yolo_cx(self, frame: np.ndarray) -> float | None:
        results = self._yolo.track(
            frame,
            persist=True,
            classes=self._preset.track_classes,
            conf=self._preset.yolo_conf,
            verbose=False,
        )
        if results and results[0].boxes and len(results[0].boxes.xywhn) > 0:
            boxes = results[0].boxes.xywhn.cpu().numpy()
            # Pick the box closest to horizontal centre
            cx_values = boxes[:, 0]
            best = cx_values[np.argmin(np.abs(cx_values - 0.5))]
            return float(best)
        return None

    def _mp_cx(self, frame: np.ndarray) -> float | None:
        if self._mp_face is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._mp_face.process(rgb)
        if res.detections:
            bb = res.detections[0].location_data.relative_bounding_box
            return float(bb.xmin + bb.width / 2)
        return None

    def track_frame(self, frame: np.ndarray, prev_cx: float) -> float:
        cx = self._yolo_cx(frame)
        if cx is None:
            cx = self._mp_cx(frame)
        if cx is None:
            # Drift toward centre slowly
            cx = prev_cx + (0.5 - prev_cx) * 0.05
        return cx


# ─── Split-screen compositor ──────────────────────────────────────────────────

def create_split_screen(
    gameplay_path: Path,
    webcam_path: Path | None,
    output_path: Path,
    target_w: int = 1080,
    target_h: int = 1920,
) -> Path:
    """
    Stack gameplay (top 65%) and webcam facecam (bottom 35%) vertically.
    If no webcam feed is supplied, use a blurred-zoom of the gameplay
    as the background — the classic "dual pane" TikTok aesthetic.
    """
    top_h = int(target_h * 0.65)
    bot_h = target_h - top_h

    if webcam_path and webcam_path.exists():
        filter_complex = (
            f"[0:v]scale={target_w}:{top_h},setsar=1[top];"
            f"[1:v]scale={target_w}:{bot_h},setsar=1[bot];"
            f"[top][bot]vstack=inputs=2[out]"
        )
        inputs = ["-i", str(gameplay_path), "-i", str(webcam_path)]
    else:
        # Blurred background: scale gameplay to fill full frame, blur it,
        # then overlay a properly-scaled gameplay on top.
        filter_complex = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={target_w}:{target_h},boxblur=20:5[blurred];"
            f"[fg]scale={target_w}:{top_h},setsar=1[gameplay_scaled];"
            f"[blurred][gameplay_scaled]overlay=0:{int((target_h - top_h) * 0.1)}[out]"
        )
        inputs = ["-i", str(gameplay_path)]

    cmd = [
        ffmpeg_bin(), "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",
        *video_encode_args(get_settings().export),
        *audio_encode_args(get_settings().export),
        *output_fps_args(get_settings().export),
        str(output_path),
    ]
    log.debug("split_screen_ffmpeg", cmd=" ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


# ─── Main per-frame reframe engine ────────────────────────────────────────────

def _reframe_with_tracking(
    input_path: Path,
    output_path: Path,
    cfg: ReframeConfig,
    preset: _Preset,
    export_cfg: ExportConfig,
) -> Path:
    """
    Core reframe: read every frame, track subject, compute smoothed crop
    window, write output via ffmpeg pipe.
    """
    tw, th = cfg.target_width, cfg.target_height
    target_ar = tw / th  # e.g. 9/16 ≈ 0.5625, 1/1 = 1.0, 16/9 ≈ 1.778

    cap = cv2.VideoCapture(str(input_path))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Crop window: largest target-AR rectangle inside the HUD-safe band.
    # Works for both narrow (9:16) and wide (16:9, 1:1) targets.
    hud_top_px = int(src_h * preset.hud_top)
    hud_bot_px = int(src_h * preset.hud_bottom)
    usable_h = src_h - hud_top_px - hud_bot_px
    crop_w = min(src_w, int(usable_h * target_ar))
    crop_h = min(usable_h, int(crop_w / target_ar))
    # Centre the crop vertically within the HUD-safe band
    crop_y1 = hud_top_px + (usable_h - crop_h) // 2

    if crop_w >= src_w and crop_h >= src_h:
        # Crop covers the whole frame — no tracking needed, just scale.
        cap.release()
        log.info("reframe_scale_only", src=f"{src_w}x{src_h}", target=f"{tw}x{th}")
        cmd = [
            ffmpeg_bin(), "-y", "-i", str(input_path),
            "-vf", f"scale={tw}:{th},setsar=1",
            *video_encode_args(export_cfg),
            *audio_encode_args(export_cfg),
            *output_fps_args(export_cfg),
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    log.info(
        "reframe_start",
        src=f"{src_w}x{src_h}", target=f"{tw}x{th}",
        crop_window=f"{crop_w}x{crop_h}", fps=src_fps, frames=total_frames,
    )

    tracker = _SubjectTracker(preset)

    # ── Pass 1: collect raw centre-x per frame ────────────────────────────
    log.info("reframe_pass1_tracking")
    raw_cx: list[float] = []
    prev_cx = 0.5
    frame_idx = 0
    sample_every = max(1, int(src_fps / 6))  # sample at ~6 fps for speed

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_every == 0:
            small = cv2.resize(frame, (480, 270))
            prev_cx = tracker.track_frame(small, prev_cx)
        raw_cx.append(prev_cx)
        frame_idx += 1

    cap.release()

    # ── Smooth the path ───────────────────────────────────────────────────
    smooth_window = _resolve_smooth_window(preset, cfg)
    smooth_cx = _smooth_path(
        raw_cx,
        window=smooth_window,
        max_vel=preset.max_pan_velocity,
    )

    # ── Pass 2: render via FFmpeg pipe ────────────────────────────────────
    log.info("reframe_pass2_encoding")
    cap = cv2.VideoCapture(str(input_path))

    ffmpeg_in_cmd = [
        ffmpeg_bin(), "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{tw}x{th}",
        "-pix_fmt", "bgr24",
        "-r", str(src_fps),
        "-i", "pipe:0",
        # Passthrough audio
        "-i", str(input_path),
        "-map", "0:v", "-map", "1:a?",
        *video_encode_args(export_cfg),
        *audio_encode_args(export_cfg),
        *output_fps_args(export_cfg),
        str(output_path),
    ]
    proc = subprocess.Popen(ffmpeg_in_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    frame_idx = 0
    crop_y2 = crop_y1 + crop_h

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cx_norm = smooth_cx[min(frame_idx, len(smooth_cx) - 1)]

        # Compute crop x1
        x1 = int((cx_norm * src_w) - crop_w / 2)
        x1 = max(0, min(x1, src_w - crop_w))
        x2 = x1 + crop_w

        # Crop the target-AR window inside the HUD-safe band
        roi = frame[crop_y1:crop_y2, x1:x2]

        # Resize to target
        out_frame = cv2.resize(roi, (tw, th), interpolation=cv2.INTER_LANCZOS4)

        proc.stdin.write(out_frame.tobytes())
        frame_idx += 1

    proc.stdin.close()
    proc.wait()
    cap.release()

    log.info("reframe_done", output=str(output_path))
    return output_path


# ─── Public API ───────────────────────────────────────────────────────────────

def reframe(
    input_path: Path,
    output_path: Path,
    cfg: Settings,
    candidate: ClipCandidate | None = None,
    webcam_path: Path | None = None,
) -> Path:
    """
    Convert a source clip to the configured export aspect ratio
    (cfg.reframe.target_width × target_height) using the configured preset.

    Tries the full tracking engine first. Falls back to a simple
    centre-crop via FFmpeg if tracking fails (faster, less precise).

    Args:
        input_path:   The source clip (any aspect ratio).
        output_path:  Where to write the reframed output.
        cfg:          Global settings.
        candidate:    Optional ClipCandidate (used for emotion-based preset selection).
        webcam_path:  Optional webcam/facecam feed for split-screen mode.

    Returns:
        Path to the reframed output file.
    """
    rcfg = cfg.reframe
    preset_name = rcfg.preset

    # Auto-detect preset from emotion if configured as "auto"
    if preset_name == "auto" and candidate:
        if candidate.emotion in (Emotion.HYPE, Emotion.CLUTCH):
            preset_name = "fps_game"
        else:
            preset_name = "irl"

    preset = PRESETS.get(preset_name, PRESETS["fps_game"])

    try:
        if webcam_path:
            # Split-screen mode: both feeds
            tracking_path = output_path.with_stem(output_path.stem + "_tracked")
            _reframe_with_tracking(input_path, tracking_path, rcfg, preset, cfg.export)
            return create_split_screen(tracking_path, webcam_path, output_path,
                                       rcfg.target_width, rcfg.target_height)
        else:
            return _reframe_with_tracking(input_path, output_path, rcfg, preset, cfg.export)

    except Exception as exc:
        log.warning("tracking_failed_fallback", error=str(exc))
        if not rcfg.fallback_center_crop:
            raise

        # Fallback: FFmpeg centre-crop (largest target-AR rect, any orientation)
        tw, th = rcfg.target_width, rcfg.target_height
        crop_expr = (
            f"crop='min(iw,ih*{tw}/{th})':'min(ih,iw*{th}/{tw})',"
            f"scale={tw}:{th},setsar=1"
        )
        cmd = [
            ffmpeg_bin(), "-y", "-i", str(input_path),
            "-vf", crop_expr,
            *video_encode_args(cfg.export),
            *audio_encode_args(cfg.export),
            *output_fps_args(cfg.export),
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        log.info("fallback_centre_crop_done", output=str(output_path))
        return output_path


# Circular import fix
from core.models import Emotion  # noqa: E402
