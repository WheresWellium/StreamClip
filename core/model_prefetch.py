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

import errno
import threading
import time
from typing import Callable, Literal, TypedDict

import structlog

from core.config import Settings

log = structlog.get_logger(__name__)

ModelState = Literal["pending", "downloading", "ready", "failed", "skipped"]

# Actionable failure causes surfaced to the first-run UI (F6). Raw tracebacks
# are useless to a creator; these map to concrete recovery steps in the banner.
FailureCause = Literal["disk_full", "network", "permission", "unknown"]


class ModelStatus(TypedDict):
    state: ModelState
    detail: str
    elapsed_secs: float
    cause: FailureCause | None


def classify_failure(exc: BaseException) -> FailureCause:
    """Map a prefetch exception to an actionable cause for the UI (F6).

    Downloads fail for a small set of real-world reasons on a fresh Windows
    install: the disk is full, there is no network, or antivirus / a locked
    folder blocks the write. Everything else is ``unknown``.
    """
    if isinstance(exc, OSError):
        winerror = getattr(exc, "winerror", None)
        if exc.errno == errno.ENOSPC or winerror in (112, 39):  # ENOSPC / ERROR_DISK_FULL / ERROR_HANDLE_DISK_FULL
            return "disk_full"
        if exc.errno in (errno.EACCES, errno.EPERM) or winerror in (5, 32):  # access denied / sharing violation
            return "permission"
    text = f"{type(exc).__name__} {exc}".lower()
    if any(k in text for k in ("no space", "disk full", "enospc")):
        return "disk_full"
    if any(k in text for k in ("connection", "timeout", "timed out", "network", "dns", "resolve",
                                "ssl", "http", "getaddrinfo", "temporarily unavailable", "connreset")):
        return "network"
    if any(k in text for k in ("permission", "access is denied", "denied", "winerror 5",
                                "quarantine", "being used by another process")):
        return "permission"
    return "unknown"


_CAUSE_HINTS: dict[FailureCause, str] = {
    "disk_full": "Your disk is full. Free up a few GB and click Retry — models need ~1.5 GB.",
    "network": "Couldn't reach the model server. Check your internet connection and click Retry.",
    "permission": "A folder was blocked (often antivirus or a read-only install). Allow qClip in your antivirus, or reinstall to the default location, then Retry.",
    "unknown": "Model download failed. Click Retry; if it keeps failing, open Help - Report a bug with the engine log.",
}


def failure_hint(cause: FailureCause | None) -> str:
    return _CAUSE_HINTS.get(cause or "unknown", _CAUSE_HINTS["unknown"])


_lock = threading.Lock()
_status: dict[str, ModelStatus] = {}
_thread: threading.Thread | None = None


def _set(
    name: str,
    state: ModelState,
    detail: str = "",
    elapsed: float = 0.0,
    cause: FailureCause | None = None,
) -> None:
    with _lock:
        _status[name] = ModelStatus(
            state=state, detail=detail, elapsed_secs=round(elapsed, 1), cause=cause
        )


def snapshot() -> dict[str, ModelStatus]:
    """Thread-safe copy of per-model prefetch state for the health API."""
    with _lock:
        return dict(_status)


def has_failures() -> bool:
    """True when any model ended in ``failed`` (used by the first-run UI)."""
    with _lock:
        return any(s["state"] == "failed" for s in _status.values())


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
            cause = classify_failure(exc)
            _set(name, "failed", failure_hint(cause), time.perf_counter() - t0, cause=cause)
            log.warning(
                "model_prefetch_failed", model=name, cause=cause, error=str(exc)
            )


def start_prefetch(cfg: Settings) -> bool:
    """Start the background prefetch thread once. Returns False if already running."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        for name in _LOADERS:
            _status.setdefault(
                name, ModelStatus(state="pending", detail="", elapsed_secs=0.0, cause=None)
            )
        _thread = threading.Thread(target=_run, args=(cfg,), name="model-prefetch", daemon=True)
    _thread.start()
    return True


def retry_prefetch(cfg: Settings) -> bool:
    """Re-run prefetch after a failure (F6 retry). Resets non-ready models to
    pending and starts a fresh thread. Returns False if one is already running.
    """
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        for name in _LOADERS:
            current = _status.get(name)
            if current is None or current["state"] != "ready":
                _status[name] = ModelStatus(
                    state="pending", detail="", elapsed_secs=0.0, cause=None
                )
        _thread = threading.Thread(target=_run, args=(cfg,), name="model-prefetch", daemon=True)
    _thread.start()
    return True
