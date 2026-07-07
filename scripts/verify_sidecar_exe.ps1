# Smoke test the PyInstaller sidecar bundle (ADR-001 section 4.6).
# Boots dist\streamclip-sidecar\streamclip-sidecar.exe against a temp data dir,
# waits for /api/health, checks /api/health/models, then shuts down.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$exe = "dist\streamclip-sidecar\streamclip-sidecar.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Missing $exe - run scripts\build_sidecar.ps1 first." -ForegroundColor Red
    exit 1
}

$dataDir = Join-Path $env:TEMP ("streamclip-sidecar-smoke-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$port = 8799

$env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
$env:STREAMCLIP_SIDECAR_PORT = "$port"
$env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"   # smoke test should not download models

Write-Host "Starting sidecar exe (data dir: $dataDir, port: $port)..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $exe -PassThru -NoNewWindow `
    -RedirectStandardOutput "$dataDir-out.log" -RedirectStandardError "$dataDir-err.log"

$healthy = $false
try {
    foreach ($i in 1..60) {
        Start-Sleep -Seconds 2
        if ($proc.HasExited) {
            Write-Host "Sidecar exited early (code $($proc.ExitCode)). Last stderr:" -ForegroundColor Red
            Get-Content "$dataDir-err.log" -Tail 40
            exit 1
        }
        try {
            $resp = Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 3
            Write-Host "Health: status=$($resp.status) db=$($resp.database) storage=$($resp.storage)"
            $models = Invoke-RestMethod "http://127.0.0.1:$port/api/health/models" -TimeoutSec 3
            Write-Host "Models endpoint: ready=$($models.ready)"
            $healthy = $true
            break
        } catch {
            if ($i % 10 -eq 0) { Write-Host "  waiting for health ($($i * 2)s)..." }
        }
    }
} finally {
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Remove-Item Env:\STREAMCLIP_DESKTOP_DATA_DIR, Env:\STREAMCLIP_SIDECAR_PORT, Env:\STREAMCLIP_SIDECAR_SKIP_PREFETCH -ErrorAction SilentlyContinue
}

if (-not $healthy) {
    Write-Host "Sidecar never became healthy within 120s. Logs: $dataDir-out.log / $dataDir-err.log" -ForegroundColor Red
    exit 1
}

# Migrations must have created the SQLite DB in the data dir.
if (-not (Test-Path (Join-Path $dataDir "streamclip.db"))) {
    Write-Host "SQLite DB missing from data dir - migrations did not run." -ForegroundColor Red
    exit 1
}

Write-Host "Sidecar exe smoke test passed." -ForegroundColor Green
