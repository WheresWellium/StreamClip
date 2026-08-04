# Prove tester VOD reaches past ingest on SOURCE-TREE desktop (Client-ID in desktop.yaml).
# Does NOT wait for full 13h pipeline. Pass = stage past download OR done.
param(
  [string]$TwitchUrl = "https://www.twitch.tv/videos/2836776596",
  [int]$Port = 18769,
  [int]$TimeoutMinutes = 20
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dataDir = Join-Path $root "tmp\proof-vod-ingest-$stamp"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$dbPath = ((Join-Path $dataDir "streamclip.db") -replace '\\', '/')

$env:PATH = "$(Join-Path $root 'bin\ffmpeg');$(Join-Path $root 'bin\yt-dlp');" + $env:PATH
$env:STREAMCLIP_CONFIG = (Resolve-Path (Join-Path $root "config\desktop.yaml")).Path
$env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
$env:STREAMCLIP_DATABASE__URL = "sqlite+aiosqlite:///$dbPath"
$env:STREAMCLIP_DATABASE__SYNC_URL = "sqlite:///$dbPath"
$env:STREAMCLIP_SIDECAR_PORT = "$Port"
$env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"
$env:STREAMCLIP_OVERLAY__ENABLED = "false"
$env:STREAMCLIP_WHISPER__MODEL_SIZE = "tiny"
$env:STREAMCLIP_WHISPER__DEVICE = "cpu"
$env:STREAMCLIP_WHISPER__COMPUTE_TYPE = "int8"

$headers = @{ "Content-Type" = "application/json"; "X-Device-Id" = "smoke0123456789abcdef0123456789ab" }
$base = "http://127.0.0.1:$Port"
$proc = $null
$pass = $false
try {
  $proc = Start-Process python -ArgumentList @("-m", "desktop_sidecar") -WorkingDirectory $root -PassThru -NoNewWindow `
    -RedirectStandardOutput (Join-Path $dataDir "out.log") -RedirectStandardError (Join-Path $dataDir "err.log")
  $healthy = $false
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep 2
    if ($proc.HasExited) { throw "sidecar exited $($proc.ExitCode)" }
    try {
      $h = Invoke-RestMethod "$base/api/health" -TimeoutSec 2
      if ($h.database -or $h.status) { $healthy = $true; break }
    } catch {}
  }
  if (-not $healthy) { throw "never healthy" }
  Write-Host "healthy"
  $job = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" -Headers $headers -Body (@{
      source_url = $TwitchUrl; target_clips = 1
    } | ConvertTo-Json)
  Write-Host "job=$($job.id)"
  $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
  $last = ""
  while ((Get-Date) -lt $deadline) {
    Start-Sleep 5
    if ($proc.HasExited) { throw "sidecar died" }
    $j = Invoke-RestMethod "$base/api/jobs/$($job.id)" -Headers $headers
    $line = "status=$($j.status) stage=$($j.current_stage) p=$($j.progress) err=$($j.error_message)"
    if ($line -ne $last) { Write-Host $line; $last = $line }
    $stage = "$($j.current_stage)"
    $prog = 0.0; try { $prog = [double]$j.progress } catch {}
    if ($j.status -in @("done", "completed") -or $stage -match "transcrib|highlight|virality|process_clip|final" -or $prog -gt 0.2) {
      Write-Host "PASS_INGEST_TESTER_VOD"
      $pass = $true
      break
    }
    if ($j.status -eq "error" -or $j.error_code) {
      throw "job failed: $($j.error_code) $($j.error_message)"
    }
  }
  if (-not $pass) { throw "timeout waiting past ingest: $last" }
}
finally {
  if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
  Remove-Item Env:STREAMCLIP_CONFIG, Env:STREAMCLIP_DESKTOP_DATA_DIR, Env:STREAMCLIP_DATABASE__URL,
    Env:STREAMCLIP_DATABASE__SYNC_URL, Env:STREAMCLIP_SIDECAR_PORT, Env:STREAMCLIP_SIDECAR_SKIP_PREFETCH,
    Env:STREAMCLIP_OVERLAY__ENABLED, Env:STREAMCLIP_WHISPER__MODEL_SIZE, Env:STREAMCLIP_WHISPER__DEVICE,
    Env:STREAMCLIP_WHISPER__COMPUTE_TYPE -ErrorAction SilentlyContinue
}
if (-not $pass) { exit 1 }
exit 0
