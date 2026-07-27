# qClip — check stack health (run in a second terminal while start.ps1 is running)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "qClip health check" -ForegroundColor Cyan
Write-Host ""

function Test-Port($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($c) { return "LISTENING" }
    return "not listening"
}

Write-Host ("Port 3000 (web):     " + (Test-Port 3000))
Write-Host ("Port 8000 (api):     " + (Test-Port 8000))
Write-Host ("Port 5432 (postgres):" + (Test-Port 5432))
Write-Host ""

try {
    $h = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 3
    Write-Host "API health: $($h.status)" -ForegroundColor Green
} catch {
    Write-Host "API health: unreachable (stack may still be starting)" -ForegroundColor Yellow
}

try {
    $m = Invoke-RestMethod -Uri "http://localhost:8000/api/meta" -TimeoutSec 3
    Write-Host "Pipeline mode: $($m.pipeline_mode)" -ForegroundColor Green
} catch { }

Write-Host ""
Write-Host "Open http://localhost:3000 when port 3000 shows LISTENING."
