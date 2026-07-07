# Verify desktop embedded-runtime profile (ADR-001 §4.1–4.5).
# Runs SQLite, in-process queue, local storage, and ffmpeg resolution smoke tests.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

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
Write-Host "Optional: in-process stack against Docker API (requires Docker running):"
Write-Host "  .\scripts\verify_inprocess.ps1"

Write-Host ""
Write-Host "Desktop profile verification passed." -ForegroundColor Green
