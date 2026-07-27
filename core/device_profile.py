"""Hardware inventory and processing recommendation for desktop setup."""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.config import Settings, get_settings
from core.gpu_profile import cuda_available, is_darwin, mps_available, nvenc_available


@dataclass(frozen=True)
class DeviceProfile:
    cpu_model: str
    cpu_cores: int
    ram_total_gb: float | None
    disk_path: str
    disk_total_gb: float
    disk_free_gb: float
    cuda: bool
    nvenc: bool
    mps: bool
    processing_mode: str
    recommendation: str
    recommendation_detail: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cpu_model() -> str:
    if is_darwin():
        brand = platform.processor() or ""
        if brand:
            return brand
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine() or "Unknown CPU"


def _ram_total_gb() -> float | None:
    try:
        import psutil  # type: ignore[import-untyped]

        return round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        pass
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round((pages * page_size) / (1024**3), 1)
    except (AttributeError, OSError, ValueError):
        return None


def _storage_root(cfg: Settings) -> Path:
    root = Path(cfg.storage.local_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return root


def _dir_used_bytes(root: Path, *, max_entries: int = 50_000) -> int:
    """Best-effort used size under *root* (capped walk for responsiveness)."""
    if not root.is_dir():
        return 0
    total = 0
    seen = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            seen += 1
            if seen > max_entries:
                return total
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                continue
    return total


def build_device_profile(cfg: Settings | None = None) -> DeviceProfile:
    settings = cfg or get_settings()
    root = _storage_root(settings)
    usage = shutil.disk_usage(str(root if root.exists() else Path.cwd()))
    cuda = cuda_available()
    nvenc = nvenc_available(settings)
    mps = mps_available()

    if cuda and nvenc:
        mode = "gpu_nvenc"
        rec = "GPU ready — fastest clip jobs on this device"
        detail = (
            "CUDA and hardware encode (NVENC) are available. "
            "qClip will use them automatically for transcription and export."
        )
    elif cuda:
        mode = "gpu_cuda"
        rec = "GPU transcription ready; software encode"
        detail = (
            "A CUDA GPU is available for transcription. Video export will use "
            "software encode (slower than NVENC)."
        )
    elif mps:
        mode = "apple_silicon"
        rec = "Apple Silicon GPU ready"
        detail = (
            "Metal (MPS) acceleration is available. Clip jobs on this Mac should "
            "run faster than a pure CPU setup."
        )
    else:
        mode = "cpu"
        rec = "CPU mode — reliable, slower on long videos"
        detail = (
            "No supported GPU acceleration was detected. Jobs still work; "
            "prefer shorter sources first, or use a machine with NVIDIA/Apple Silicon."
        )

    cores = os.cpu_count() or 1
    return DeviceProfile(
        cpu_model=_cpu_model(),
        cpu_cores=cores,
        ram_total_gb=_ram_total_gb(),
        disk_path=str(root.resolve()),
        disk_total_gb=round(usage.total / (1024**3), 1),
        disk_free_gb=round(usage.free / (1024**3), 1),
        cuda=cuda,
        nvenc=nvenc,
        mps=mps,
        processing_mode=mode,
        recommendation=rec,
        recommendation_detail=detail,
    )


def build_storage_status(cfg: Settings | None = None) -> dict[str, Any]:
    settings = cfg or get_settings()
    backend = settings.storage.backend
    if backend != "local":
        return {
            "backend": backend,
            "label": "External object storage",
            "root": None,
            "used_bytes": None,
            "free_bytes": None,
            "total_bytes": None,
            "human_root": None,
            "advanced": True,
        }

    root = _storage_root(settings)
    usage = shutil.disk_usage(str(root if root.exists() else Path.cwd()))
    used = _dir_used_bytes(root)
    return {
        "backend": "local",
        "label": "Saved on this device",
        "root": str(root.resolve()),
        "used_bytes": used,
        "free_bytes": usage.free,
        "total_bytes": usage.total,
        "human_root": str(root.resolve()),
        "advanced": False,
    }
