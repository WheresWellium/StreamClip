# One-shot OPS_WEBHOOK_URL mock verify (no Discord/Sentry secrets required).
# Starts a local HTTP receiver, POSTs a synthetic payload from the api container
# via host.docker.internal, asserts JSON arrived, then tears down.
#
# Usage (repo root, stack up):
#   .\scripts\verify_ops_webhook.ps1
param(
    [int]$Port = 18765,
    [int]$TimeoutSec = 20
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$outFile = Join-Path $env:TEMP "streamclip-ops-webhook-verify.jsonl"
if (Test-Path $outFile) { Remove-Item $outFile -Force }

$receiverPy = @"
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

OUT = sys.argv[1]
PORT = int(sys.argv[2])

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        with open(OUT, "ab") as f:
            f.write(body + b"\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *args):
        return

HTTPServer(("0.0.0.0", PORT), H).handle_request()
"@

$pyFile = Join-Path $env:TEMP "streamclip_ops_receiver.py"
Set-Content -Path $pyFile -Value $receiverPy -Encoding utf8

Write-Host "Starting mock OPS receiver on :$Port ..." -ForegroundColor Cyan
$proc = Start-Process -FilePath "python" -ArgumentList @($pyFile, $outFile, "$Port") `
    -PassThru -WindowStyle Hidden

try {
    # Give the listener a moment before the container POSTs (avoids first-attempt refuse).
    Start-Sleep -Milliseconds 800
    if ($proc.HasExited) {
        Write-Host "FAIL: mock receiver exited early (exit $($proc.ExitCode))" -ForegroundColor Red
        exit 1
    }

    $hook = "http://host.docker.internal:$Port/ops"
    Write-Host "POSTing synthetic payload from api container -> $hook" -ForegroundColor Cyan
    docker compose exec -T -e "OPS_WEBHOOK_URL=$hook" api python -c @"
from core.notify.ops_webhook import post_ops_webhook
ok = post_ops_webhook({
    'event': 'ops_webhook_verify',
    'app': 'streamclip',
    'message': 'verify_ops_webhook.ps1 synthetic probe',
})
print('POST_OK' if ok else 'POST_FAIL')
raise SystemExit(0 if ok else 1)
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: post_ops_webhook returned false (container cannot reach host:$Port?)" -ForegroundColor Red
        exit 1
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path $outFile) -and ((Get-Item $outFile).Length -gt 0)) { break }
        Start-Sleep -Milliseconds 200
    }

    if (-not (Test-Path $outFile) -or ((Get-Item $outFile).Length -eq 0)) {
        Write-Host "FAIL: no payload received at mock receiver" -ForegroundColor Red
        exit 1
    }

    $body = Get-Content $outFile -Raw
    if ($body -notmatch 'ops_webhook_verify') {
        Write-Host "FAIL: payload missing event ops_webhook_verify" -ForegroundColor Red
        Write-Host $body
        exit 1
    }

    Write-Host "PASS: OPS webhook path verified (mock received ops_webhook_verify)." -ForegroundColor Green
    Write-Host "Payload file: $outFile" -ForegroundColor DarkGray
    Write-Host "Next: paste a real OPS_WEBHOOK_URL into .env and restart api worker beat." -ForegroundColor Cyan
    exit 0
}
finally {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pyFile -Force -ErrorAction SilentlyContinue
}
