# Build StreamClip desktop sidecar with PyInstaller (ADR-001 section 4.6).
# Full ML bundle by default (CPU-only torch). Env toggles:
#   STREAMCLIP_SKIP_PYINSTALLER=1  scaffold tests only, no build
#   STREAMCLIP_LITE=1              API-only bundle without the ML stack (fast smoke)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$SkipBuild = $env:STREAMCLIP_SKIP_PYINSTALLER -eq "1"

Write-Host "Sidecar dry-run (imports + migration hook)..." -ForegroundColor Cyan
python -m pytest tests/test_sidecar_packaging.py tests/test_static_ui.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -c "from desktop_sidecar.run import configure_desktop_env, app_root; configure_desktop_env(); print('app_root=', app_root())"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipBuild) {
    Write-Host "STREAMCLIP_SKIP_PYINSTALLER=1 - skipping PyInstaller (scaffold tests passed)." -ForegroundColor Yellow
    exit 0
}

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing packaging requirements..."
    python -m pip install -r requirements-packaging.txt -q
}

# Critical ML imports must exist BEFORE PyInstaller. collect_all("librosa") can
# "succeed" with an empty result when the package is missing (builds a silent
# brick that crashes at run_highlights). Fail fast and install the desktop profile.
# Prefer a tiny helper script so PowerShell quoting cannot strip Python string literals.
$mlProbe = Join-Path $PSScriptRoot "_probe_ml_imports.py"
@'
import importlib
import sys
for name in (
    "librosa", "soundfile", "torch", "ctranslate2", "faster_whisper",
    "ollama", "ultralytics", "mediapipe",
):
    importlib.import_module(name)
print("ok")
sys.exit(0)
'@ | Set-Content -Path $mlProbe -Encoding ascii
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $mlCheck = & python $mlProbe 2>&1 | Out-String
    $mlCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $prevEap
    Remove-Item $mlProbe -ErrorAction SilentlyContinue
}
if ($mlCode -ne 0 -or ($mlCheck -notmatch "ok")) {
    Write-Host "Critical ML packages missing in this Python - installing requirements-desktop.txt ..." -ForegroundColor Yellow
    Write-Host $mlCheck
    python -m pip install -r requirements-desktop.txt -r requirements-packaging.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $ErrorActionPreference = "Continue"
    try {
        $mlRecheck = & python -c "import librosa,soundfile,torch,ctranslate2,faster_whisper,ollama,ultralytics,mediapipe; print('ml_ok')" 2>&1 | Out-String
        $mlRecheckCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($mlRecheckCode -ne 0 -or ($mlRecheck -notmatch "ml_ok")) {
        Write-Host "FATAL: ML packages still missing after pip install." -ForegroundColor Red
        Write-Host $mlRecheck
        exit 1
    }
}

# Warn if CUDA torch is installed - bundle will be ~2 GB heavier than needed.
$ErrorActionPreference = "Continue"
try {
    $cudaCheck = & python -c "import torch; print('cuda' if torch.version.cuda else 'cpu')" 2>$null
} finally {
    $ErrorActionPreference = $prevEap
}
if ($cudaCheck -eq "cuda") {
    Write-Host "WARNING: CUDA torch detected. For a lean bundle use a venv with:" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements-desktop.txt -r requirements-packaging.txt" -ForegroundColor Yellow
}

Write-Host "Running PyInstaller one-dir build (may take several minutes)..." -ForegroundColor Cyan
python -m PyInstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exe = "dist\streamclip-sidecar\streamclip-sidecar.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build finished but $exe not found." -ForegroundColor Red
    exit 1
}
# Post-build: prove the modules that silently vanished from earlier releases.
$internal = "dist\streamclip-sidecar\_internal"
$mustExist = @(
    (Join-Path $internal "librosa"),
    (Join-Path $internal "soundfile.py"),
    (Join-Path $internal "_soundfile_data"),
    (Join-Path $internal "ultralytics"),
    (Join-Path $internal "mediapipe"),
    (Join-Path $internal "ollama"),
    (Join-Path $internal "matplotlib")
)
$missing = @($mustExist | Where-Object { -not (Test-Path $_) })
if ($missing.Count -gt 0) {
    Write-Host "FATAL: sidecar bundle missing required ML assets:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
$sizeMB = [math]::Round((Get-ChildItem dist\streamclip-sidecar -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Write-Host ('Sidecar build complete: dist\streamclip-sidecar ({0} MB)' -f $sizeMB) -ForegroundColor Green
Write-Host "Smoke test: .\scripts\verify_sidecar_exe.ps1" -ForegroundColor Cyan
