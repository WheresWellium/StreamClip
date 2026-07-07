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

# Warn if CUDA torch is installed - bundle will be ~2 GB heavier than needed.
$cudaCheck = python -c "import torch; print('cuda' if torch.version.cuda else 'cpu')" 2>$null
if ($cudaCheck -eq "cuda") {
    Write-Host "WARNING: CUDA torch detected. For a lean bundle use a venv with:" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements-desktop.txt -r requirements-packaging.txt" -ForegroundColor Yellow
}

Write-Host "Running PyInstaller one-dir build (may take several minutes)..." -ForegroundColor Cyan
pyinstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exe = "dist\streamclip-sidecar\streamclip-sidecar.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build finished but $exe not found." -ForegroundColor Red
    exit 1
}
$sizeMB = [math]::Round((Get-ChildItem dist\streamclip-sidecar -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Write-Host "Sidecar build complete: dist\streamclip-sidecar ($sizeMB MB)" -ForegroundColor Green
Write-Host "Smoke test: .\scripts\verify_sidecar_exe.ps1" -ForegroundColor Cyan
