# Clean-desktop-VM pre-flight (product ship gate).
# Boots the desktop sidecar against a THROWAWAY per-user data dir to catch the
# fresh-install failure classes without a full install:
#   F1  writable-path fail-fast (read-only prefix -> SystemExit, not white screen)
#   F5  Alembic migrations apply on a brand-new SQLite DB
#   F12 config/desktop.yaml overrides land before backend import
# See docs/CLEAN_DESKTOP_VM_VERIFY.md for the full manual gate.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Snapshot env we mutate so chained sibling scripts can't leak a stale port /
# data dir into this gate (root cause of an earlier cross-gate collision).
$_envKeys = @(
    "STREAMCLIP_DESKTOP_DATA_DIR", "STREAMCLIP_SIDECAR_PORT",
    "STREAMCLIP_SIDECAR_SKIP_PREFETCH", "STREAMCLIP_DATABASE__URL",
    "STREAMCLIP_DATABASE__SYNC_URL"
)
$_envSaved = @{}
foreach ($k in $_envKeys) { $_envSaved[$k] = [Environment]::GetEnvironmentVariable($k) }
function Restore-Env {
    foreach ($k in $script:_envKeys) {
        if ($null -eq $script:_envSaved[$k]) {
            Remove-Item "Env:$k" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:$k" $script:_envSaved[$k]
        }
    }
}
function Exit-Restored([int]$code) { Restore-Env; exit $code }

# Run the battery FIRST, before setting our own env, so its sub-scripts run in a
# clean environment and cannot collide with our boot below.
Write-Host "=== desktop profile smoke ===" -ForegroundColor Cyan
& "$PSScriptRoot\verify_desktop.ps1"
if ($LASTEXITCODE -ne 0) { Exit-Restored $LASTEXITCODE }

# Fresh data dir so we always exercise the first-run path, never a warm cache.
# A leaked DB URL from a sibling script would point us at the wrong DB — clear them.
Remove-Item Env:STREAMCLIP_DATABASE__URL -ErrorAction SilentlyContinue
Remove-Item Env:STREAMCLIP_DATABASE__SYNC_URL -ErrorAction SilentlyContinue
$dataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("qclip-clean-" + [guid]::NewGuid().ToString("N"))
$port = 8799
$env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
$env:STREAMCLIP_SIDECAR_PORT = "$port"
$env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"   # model download is covered by the manual VM gate

Write-Host ""
Write-Host "=== fresh-data-dir sidecar boot (data: $dataDir) ===" -ForegroundColor Cyan
$sidecar = Start-Process -FilePath "python" -ArgumentList "-m", "desktop_sidecar" -PassThru -NoNewWindow

$healthy = $false
try {
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        try {
            $res = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/health" -UseBasicParsing -TimeoutSec 3
            if ($res.StatusCode -eq 200) { $healthy = $true; break }
        } catch { }
        if ($sidecar.HasExited) { break }
    }
} finally {
    if (-not $sidecar.HasExited) { $sidecar | Stop-Process -Force }
}

if (-not $healthy) {
    Write-Host "FAIL: sidecar did not become healthy on a fresh data dir." -ForegroundColor Red
    Write-Host "      Check the writable fail-fast (F1) and migrations (F5)." -ForegroundColor Red
    Exit-Restored 1
}

# Confirm the first-run artifacts the manual gate depends on actually appeared.
$dbFile = Join-Path $dataDir "streamclip.db"
if (-not (Test-Path $dbFile)) {
    Write-Host "FAIL: SQLite DB not created at $dbFile (migrations did not run)." -ForegroundColor Red
    Exit-Restored 1
}

Write-Host ""
Write-Host "Cleaning up throwaway data dir..." -ForegroundColor DarkGray
Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Clean-desktop pre-flight PASSED. Now run the manual VM gate:" -ForegroundColor Green
Write-Host "  docs/CLEAN_DESKTOP_VM_VERIFY.md" -ForegroundColor Green
Restore-Env
