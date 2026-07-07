# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — StreamClip desktop sidecar (ADR-001 §4.6).

Build (from repo root, venv with full requirements + requirements-packaging.txt):

    pyinstaller packaging/pyinstaller/streamclip-sidecar.spec

Output: dist/streamclip-sidecar/ (one-dir; torch/whisper make one-file impractical).

This is a **scaffold**: full ML stack bundling is tracked in MASTER_TODO §4.6
(CPU-only wheels, ONNX YOLO, first-run model download §4.8).
"""

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).resolve().parents[1]
a = Analysis(
    [str(ROOT / "desktop_sidecar" / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "config" / "desktop.yaml"), "config"),
        (str(ROOT / "alembic.ini"), "."),
        (str(ROOT / "alembic"), "alembic"),
        (str(ROOT / "config" / "profanity_en.txt"), "config"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "alembic",
        "backend.main",
        "core.inprocess_worker",
        "core.tasks.pipeline_tasks",
        "core.tasks.publish_tasks",
        "core.tasks.vault_tasks",
        "core.tasks.notify_tasks",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
