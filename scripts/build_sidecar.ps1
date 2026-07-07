# Build StreamClip desktop sidecar with PyInstaller (ADR-001 section 4.6).
# Full build is multi-GB (torch/whisper) - this script validates the scaffold.
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

Write-Host "Running PyInstaller one-dir build (may take several minutes)..." -ForegroundColor Cyan
pyinstaller packaging/pyinstaller/streamclip-sidecar.spec --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Sidecar build complete: dist\streamclip-sidecar" -ForegroundColor Green
