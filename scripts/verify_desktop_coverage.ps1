# Desktop seam coverage gate (product-path ratchet).
#
# The canonical Docker gate (verify_coverage.ps1) runs `-m "not desktop"` and
# therefore CANNOT see the desktop runtime seam — the exact code that breaks for
# other Windows users (taxonomy F10). This gate measures ONLY the desktop seam
# modules, using the desktop-marked + seam tests, so drift there fails loudly
# instead of hiding behind a waiver.
#
# Usage:
#   .\scripts\verify_desktop_coverage.ps1                 # default threshold
#   .\scripts\verify_desktop_coverage.ps1 -FailUnder 85   # custom threshold
#
# Runs locally (no Docker) — the desktop profile is Docker-free by design.
# Baseline at introduction was 91% (2026-07-31); gate set at 85 to catch
# regressions while leaving headroom. Ratchet up as seam tests are added.
param(
    [int]$FailUnder = 85
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# The desktop runtime seam — the modules that only exist / only run in the
# embedded .exe path and are excluded from the Docker coverage gate. Coverage
# takes module import names (dotted) so the measurement attaches reliably.
$seam = @(
    "core.inprocess_worker",
    "core.progress_bus",
    "core.task_dispatch",
    "core.task_runner",
    "core.gpu_profile",
    "core.model_prefetch",
    "backend.static_ui",
    "desktop_sidecar.run"
)

# Tests that exercise the seam. Scoped to the self-contained seam tests: the
# license-seed / config tests need a fresh DB-engine singleton and are covered
# by scripts/verify_desktop.ps1 in the correct isolation, so they are run there,
# not batched here (batching them re-uses a cached Postgres engine — a test
# ordering artifact, not a product bug).
$tests = @(
    "tests/test_inprocess_worker.py",
    "tests/test_progress_bus.py",
    "tests/test_task_dispatch.py",
    "tests/test_gpu_profile.py",
    "tests/test_model_prefetch.py",
    "tests/test_static_ui.py",
    "tests/test_sse_inprocess.py",
    "tests/test_sidecar_packaging.py"
)

$covArgs = @()
foreach ($m in $seam) { $covArgs += "--cov=$m" }

Write-Host "=== Desktop seam coverage gate (fail-under $FailUnder%) ===" -ForegroundColor Cyan
Write-Host "Seam modules:" -ForegroundColor DarkGray
$seam | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
Write-Host ""

# -p no:cacheprovider + explicit cov overrides so pytest.ini's backend/core
# global cov config does not dilute the seam measurement.
python -m pytest $tests `
    $covArgs `
    --cov-report=term-missing `
    --cov-fail-under=$FailUnder `
    --no-header `
    -o addopts="" `
    -q
$code = $LASTEXITCODE

Write-Host ""
if ($code -eq 0) {
    Write-Host "Desktop seam coverage PASSED (>= $FailUnder%)." -ForegroundColor Green
} else {
    Write-Host "Desktop seam coverage FAILED. Add a regression test for the uncovered seam line," -ForegroundColor Red
    Write-Host "then map it to a taxonomy F-class in docs/DESKTOP_FAILURE_TAXONOMY.md." -ForegroundColor Red
}
exit $code
