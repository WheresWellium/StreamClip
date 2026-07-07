"""
First-run ML model prefetch for the desktop profile (MASTER_TODO §4.8).

Downloads happen lazily on first job otherwise, which makes the first clip
feel broken (multi-minute silent stall inside transcribe/reframe). The
sidecar starts a background prefetch at boot so models are warm by the time
the user submits a job; ``/api/health/models`` exposes progress for the UI.

Import direction: backend and desktop_sidecar both import this module;
it only imports core config. ML libraries load inside the worker thread.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Literal, TypedDict

import structlog

from core.config import Settings

log = structlog.get_logger(__name__)

ModelState = Literal["pending", "downloading", "ready", "failed", "skipped"]


class ModelStatus(TypedDict):
    state: ModelState
    detail: str
    elapsed_secs: float


_lock = threading.Lock()
_status: dict[str, ModelStatus] = {}
_thread: threading.Thread | None = None


def _set(name: str, state: ModelState, detail: str = "", elapsed: float = 0.0) -> None:
    with _lock:
        _status[name] = ModelStatus(state=state, detail=detail, elapsed_secs=round(elapsed, 1))


def snapshot() -> dict[str, ModelStatus]:
    """Thread-safe copy of per-model prefetch state for the health API."""
    with _lock:
        return dict(_status)


def _load_whisper(cfg: Settings) -> str:
    from faster_whisper import WhisperModel

    # CPU-safe instantiation triggers the HuggingFace download; the pipeline
    # loads its own device-appropriate instance later from the same cache.
    WhisperModel(cfg.whisper.model_size, device="cpu", compute_type="int8")
    return f"faster-whisper {cfg.whisper.model_size}"


def _load_yolo(cfg: Settings) -> str:
    from ultralytics import YOLO

    YOLO("yolo11n.pt")
    return "yolo11n"


def _load_embedder(cfg: Settings) -> str:
    from sentence_transformers import SentenceTransformer

    SentenceTransformer("all-MiniLM-L6-v2")
    return "all-MiniLM-L6-v2"


_LOADERS: dict[str, Callable[[Settings], str]] = {
    "whisper": _load_whisper,
    "yolo": _load_yolo,
    "embedder": _load_embedder,
}


def _run(cfg: Settings) -> None:
    for name, loader in _LOADERS.items():
        t0 = time.perf_counter()
        _set(name, "downloading")
        try:
            detail = loader(cfg)
            _set(name, "ready", detail, time.perf_counter() - t0)
            log.info("model_prefetch_ready", model=name, secs=round(time.perf_counter() - t0, 1))
        except ImportError as exc:
            _set(name, "skipped", f"dependency missing: {exc.name}", time.perf_counter() - t0)
            log.warning("model_prefetch_skipped", model=name, missing=exc.name)
        except Exception as exc:  # noqa: BLE001 — prefetch must never crash the app
            _set(name, "failed", str(exc), time.perf_counter() - t0)
            log.warning("model_prefetch_failed", model=name, error=str(exc))


def start_prefetch(cfg: Settings) -> bool:
    """Start the background prefetch thread once. Returns False if already running."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        for name in _LOADERS:
            _status.setdefault(name, ModelStatus(state="pending", detail="", elapsed_secs=0.0))
        _thread = threading.Thread(target=_run, args=(cfg,), name="model-prefetch", daemon=True)
    _thread.start()
    return True
