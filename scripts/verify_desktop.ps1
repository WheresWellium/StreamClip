# Verify desktop embedded-runtime profile (ADR-001 §4.1–4.5).
# Docker-free: host Python + pytest only. Does not start compose or call Docker.
# Runs SQLite, local storage, ffmpeg resolution, sidecar packaging, and installer-config smoke tests.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Desktop verification (no Docker required)." -ForegroundColor Cyan

$scripts = @(
    "verify_desktop_db.ps1",
    "verify_desktop_storage.ps1",
    "verify_desktop_ffmpeg.ps1"
)

foreach ($s in $scripts) {
    Write-Host ""
    Write-Host "=== $s ===" -ForegroundColor Cyan
    & "$PSScriptRoot\$s"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "=== sidecar + static UI scaffold ===" -ForegroundColor Cyan
python -m pytest tests/test_sidecar_packaging.py tests/test_static_ui.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== model prefetch + Windows path handling ===" -ForegroundColor Cyan
python -m pytest tests/test_model_prefetch.py tests/test_splice_module.py tests/test_installer_config.py -q --no-cov --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Skipped (optional, Docker): .\scripts\verify_inprocess.ps1 — not part of desktop-only verify."
Write-Host ""
Write-Host "Desktop profile verification passed." -ForegroundColor Green
