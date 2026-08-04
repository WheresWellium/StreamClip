# Turnkey desktop pre-ship gate (one command).
#
# Runs EVERYTHING that can be automated on the build host, then prints the
# operator-only manual steps that MUST be performed on a clean Windows 11 VM.
# It never fakes cohort/VM evidence — those are printed as a checklist for a human.
#
# Automatable (this script, blocks on failure):
#   - desktop profile smoke (db / storage / ffmpeg / sidecar scaffold)
#   - desktop seam coverage gate (F10)
#   - desktop upgrade simulation (F5)
#   - fresh-data-dir sidecar boot (F1/F5/F12)
#   - signing readiness preflight (F9) — informational unless -RequireSigning
#
# Operator-only (printed, not automated — do NOT invent results):
#   - install the actual .exe on a clean VM -> first clip (docs/CLEAN_DESKTOP_VM_VERIFY.md)
#   - fill docs/DESKTOP_COHORT_EXIT.md (T0 flows, install->first-clip median, crash-free)
#
# Usage:
#   .\scripts\verify_desktop_release.ps1                 # unsigned beta pre-ship
#   .\scripts\verify_desktop_release.ps1 -RequireSigning # signed release gate
param(
    [switch]$RequireSigning
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Gate([string]$name, [scriptblock]$body) {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host "  GATE: $name" -ForegroundColor Cyan
    Write-Host "==================================================================" -ForegroundColor Cyan
    & $body
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "BLOCKED at gate: $name (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# 1. Full desktop battery: profile smoke + seam coverage (F10) + upgrade sim (F5).
Invoke-Gate "Desktop battery (smoke + coverage F10 + upgrade F5)" {
    & "$PSScriptRoot\verify_desktop.ps1"
}

# 2. Fresh-install boot smoke (F1/F5/F12) against a throwaway data dir.
Invoke-Gate "Fresh-data-dir boot smoke (F1/F5/F12)" {
    & "$PSScriptRoot\verify_desktop_clean.ps1"
}

# 3. Signing readiness (F9). Informational for beta; hard gate with -RequireSigning.
Invoke-Gate "Signing readiness (F9)" {
    if ($RequireSigning) {
        & "$PSScriptRoot\verify_desktop_signing_ready.ps1" -RequireSigning
    } else {
        & "$PSScriptRoot\verify_desktop_signing_ready.ps1" -DryRun
    }
}

# ── Automatable gates passed. Now the human part. ────────────────────────────
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  AUTOMATED PRE-SHIP GATES PASSED" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "OPERATOR-ONLY (do NOT skip; do NOT invent results):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Build + (optionally) sign + publish the installer:" -ForegroundColor Yellow
if ($RequireSigning) {
    Write-Host "       .\scripts\publish_desktop_release.ps1 -RequireSigned" -ForegroundColor Yellow
} else {
    Write-Host "       .\scripts\publish_desktop_release.ps1" -ForegroundColor Yellow
    Write-Host "       (unsigned beta: testers use SmartScreen 'More info -> Run anyway')" -ForegroundColor DarkYellow
}
Write-Host ""
Write-Host "  2. On a CLEAN Windows 11 VM (no prior %LOCALAPPDATA%\StreamClip):" -ForegroundColor Yellow
Write-Host "       - install the .exe, launch, activate license, make first clip" -ForegroundColor Yellow
Write-Host "       - follow docs\CLEAN_DESKTOP_VM_VERIFY.md and fill the sign-off" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Record cohort results in docs\DESKTOP_COHORT_EXIT.md:" -ForegroundColor Yellow
Write-Host "       - T0-1..T0-4, install->first-clip median (<45m), crash-free (>98%)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Optional host rechecks (not a substitute for clean-VM):" -ForegroundColor DarkGray
Write-Host "  .\scripts\run_e2e_full.ps1 -ApiBase http://127.0.0.1:8765" -ForegroundColor DarkGray
Write-Host "  python scripts\matrix_create_pipeline_timing.py --summarize-only" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Ship gate = automated (above) + the clean-VM sign-off. The VM run and" -ForegroundColor Yellow
Write-Host "  cohort numbers are human evidence and are intentionally NOT automated." -ForegroundColor Yellow
Write-Host ""
Write-Host "Desktop release pre-flight complete." -ForegroundColor Green
