# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — StreamClip desktop sidecar (ADR-001 §4.6, full ML bundle).

Build (from repo root, venv with requirements-desktop.txt + requirements-packaging.txt):

    pyinstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm

Output: dist/streamclip-sidecar/ (one-dir; the ML stack makes one-file impractical).

Bundle strategy:
  • CPU-only torch wheels (see requirements-desktop.txt) — no CUDA DLLs (~2 GB saved).
  • collect_all for packages with data files / DLLs / dynamic imports
    (torch, ctranslate2, ultralytics, mediapipe, librosa, ...).
  • Model weights are NOT bundled — downloaded on first run (§4.8
    core/model_prefetch.py) into the per-user data dir.
  • Set STREAMCLIP_LITE=1 to skip the ML stack entirely (API-only smoke bundle).
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).resolve().parents[1]
LITE = os.environ.get("STREAMCLIP_LITE", "") in ("1", "true", "yes")

datas = [
    (str(ROOT / "config" / "desktop.yaml"), "config"),
    (str(ROOT / "packaging" / "cohort" / "cohort_licenses.json"), "packaging/cohort"),
    (str(ROOT / "alembic.ini"), "."),
    (str(ROOT / "alembic"), "alembic"),
    (str(ROOT / "config" / "profanity_en.txt"), "config"),
]
# Static web UI (built via scripts/build_desktop_ui.ps1) if present.
static_ui = ROOT / "static" / "ui"
if (static_ui / "index.html").exists():
    datas.append((str(static_ui), "static/ui"))
# Bundled ffmpeg binaries if present (core/ffmpeg_bins.py resolves them).
ffmpeg_dir = ROOT / "bin" / "ffmpeg"
if any(ffmpeg_dir.glob("ffmpeg*")):
    datas.append((str(ffmpeg_dir), "bin/ffmpeg"))

binaries = []
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "alembic",
    "aiosqlite",
    "backend.main",
    "core.inprocess_worker",
    "core.model_prefetch",
    "core.tasks.pipeline_tasks",
    "core.tasks.publish_tasks",
    "core.tasks.vault_tasks",
    "core.tasks.notify_tasks",
]

# Celery task decorators still load in-process (task_runner seam); celery and
# kombu resolve loaders/transports/backends by name at runtime, so their full
# submodule trees must ship.
for _pkg in ("celery", "kombu", "vine", "billiard"):
    hiddenimports += collect_submodules(_pkg, filter=lambda n: ".tests" not in n)

# ── ML stack ─────────────────────────────────────────────────────────────────
# collect_all pulls data files, DLLs, and all submodules — required for
# packages with dynamic imports (torch backends, ultralytics YAML configs,
# mediapipe .tflite graphs, librosa's lazy_loader'd submodules, ctranslate2
# and soundfile native DLLs).
ML_COLLECT_ALL = [
    "torch",
    "torchvision",
    "ctranslate2",
    "faster_whisper",
    "ultralytics",
    "mediapipe",
    "librosa",
    "soundfile",
    "scenedetect",
    "sklearn",
    "numba",
    "llvmlite",
    "lazy_loader",
]
# sentence-transformers pulls the HF stack; data-only collection suffices
# for transformers/tokenizers (weights download at runtime).
ML_COLLECT_DATA = ["transformers", "tokenizers", "sentence_transformers", "huggingface_hub"]
ML_HIDDEN = [
    "cv2",
    "sentence_transformers",
    "transformers",
    "scipy._cyutility",
]

# Critical packages: without these the core transcribe → clip path cannot run,
# so a collection failure MUST abort the build. Previously these were swallowed
# with a print(), so a misconfigured env produced a "successful" build that
# crashed on the first job. Optional packages (optical flow, scene detection,
# embeddings) degrade gracefully at runtime, so a failure there only warns.
ML_CRITICAL = {"torch", "ctranslate2", "faster_whisper"}

if not LITE:
    degraded: list[str] = []
    for pkg in ML_COLLECT_ALL:
        try:
            d, b, h = collect_all(pkg)
            datas += d
            binaries += b
            hiddenimports += h
        except Exception as exc:
            if pkg in ML_CRITICAL:
                raise SystemExit(
                    f"[spec] FATAL: collect_all({pkg!r}) failed — this package is "
                    f"required for transcription and the bundle would crash on the "
                    f"first job. Fix the packaging env and rebuild. Cause: {exc}"
                )
            print(f"[spec] WARN: optional collect_all({pkg!r}) failed (feature degrades): {exc}")
            degraded.append(pkg)
    for pkg in ML_COLLECT_DATA:
        try:
            datas += collect_data_files(pkg)
            hiddenimports += collect_submodules(pkg, filter=lambda n: ".tests" not in n)
        except Exception as exc:
            print(f"[spec] WARN: collect_data_files({pkg!r}) failed: {exc}")
            degraded.append(pkg)
    hiddenimports += ML_HIDDEN
    if degraded:
        print(f"[spec] NOTE: optional ML packages not fully bundled: {sorted(set(degraded))}")

excludes = [
    "tkinter",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "mypy",
    "ruff",
    # Postgres drivers are server-profile only; desktop is SQLite
    "asyncpg",
    "psycopg",
    # Cloud/ops-only surfaces
    "flower",
    "boto3",
    "botocore",
    "sentry_sdk",
]
if LITE:
    excludes += ML_COLLECT_ALL + ["cv2", "transformers", "sentence_transformers"]

a = Analysis(
    [str(ROOT / "desktop_sidecar" / "run.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    # ultralytics inspects its own source at runtime for config resolution
    module_collection_mode={"ultralytics": "py"} if not LITE else {},
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="streamclip-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="streamclip-sidecar",
)
