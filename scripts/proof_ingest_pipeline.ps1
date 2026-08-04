# Prove Twitch/upload honesty fixes on SOURCE-TREE desktop runtime (not installed beta).
# Pass rules:
#   - upload job status=done AND clips >= 1
#   - twitch: status=done+clips>=1 OR ingest progresses past download (Client-ID path)
#     OR honest user-facing reject (deleted/unpublished) — not a crash/React loop
# Usage:
#   .\scripts\proof_ingest_pipeline.ps1
#   .\scripts\proof_ingest_pipeline.ps1 -TwitchUrl "https://www.twitch.tv/videos/..."
#   .\scripts\proof_ingest_pipeline.ps1 -SkipTwitch

param(
  [string]$TwitchUrl = "https://www.twitch.tv/videos/2836776596",
  [string]$TwitchClipUrl = "https://www.twitch.tv/xqc/clip/StupidSavoryBunnyGOWSkull-UOULtimf_a-kocc0",
  [switch]$SkipTwitch,
  [switch]$TwitchClipOnly,
  [int]$Port = 18765,
  [int]$UploadTimeoutMinutes = 20,
  [int]$TwitchTimeoutMinutes = 30
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dataDir = Join-Path $root "tmp\proof-desktop-$stamp"
$logPath = Join-Path $root "tmp\proof-ingest-pipeline.log"
$resultPath = Join-Path $root "tmp\proof-ingest-pipeline-result.json"
New-Item -ItemType Directory -Path $dataDir, (Join-Path $root "tmp\fixtures") -Force | Out-Null
"" | Set-Content -LiteralPath $logPath -Encoding utf8

function Write-Log([string]$Message) {
  $line = "$(Get-Date -Format o) $Message"
  Write-Host $line
  Add-Content -LiteralPath $logPath -Value $line
}

function Ensure-Fixture {
  $video = Join-Path $root "tmp\fixtures\smoke_video.mp4"
  if ((Test-Path $video) -and ((Get-Item $video).Length -gt 10000)) { return $video }
  $ffmpeg = Join-Path $root "bin\ffmpeg\ffmpeg.exe"
  if (-not (Test-Path $ffmpeg)) { throw "Missing $ffmpeg" }
  Write-Log "generating fixture $video"
  & $ffmpeg -y -f lavfi -i "testsrc=size=640x360:rate=30" -f lavfi -i "sine=frequency=880:sample_rate=44100" `
    -t 20 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest $video 2>$null
  if (-not (Test-Path $video)) { throw "fixture generation failed" }
  return $video
}

$result = [ordered]@{
  stamp            = $stamp
  reject_ok        = $false
  normalize_ok     = $false
  ytdlp_probe_ok   = $false
  ytdlp_probe_detail = ""
  upload_status    = ""
  upload_clips     = 0
  upload_error     = ""
  upload_job_id    = ""
  twitch_status    = ""
  twitch_stage     = ""
  twitch_clips     = 0
  twitch_error     = ""
  twitch_job_id    = ""
  twitch_mode      = ""
  overall_pass     = $false
}

# --- URL normalize / reject (source tree) ---
$pyCheck = @"
from core.ingest.url_normalize import normalize_source_url
ok = normalize_source_url('https://www.twitch.tv/videos/2836776596')
assert '/videos/2836776596' in ok
raised = False
try:
    normalize_source_url('https://www.twitch.tv/somechannel')
except ValueError as e:
    raised = 'downloadable VOD' in str(e) or 'channel' in str(e).lower()
assert raised, 'channel URL must reject'
print('NORMALIZE_OK')
"@
$normOut = & python -c $pyCheck 2>&1
Write-Log "normalize: $normOut"
if ("$normOut" -match "NORMALIZE_OK") {
  $result.normalize_ok = $true
  $result.reject_ok = $true
} else {
  Write-Log "FAIL normalize/reject"
  $result | ConvertTo-Json | Set-Content $resultPath
  exit 2
}

# --- yt-dlp Client-ID probe (no full VOD download) ---
$ytdlp = Join-Path $root "bin\yt-dlp\yt-dlp.exe"
if (-not (Test-Path $ytdlp)) {
  $dl = Join-Path $root "scripts\download_ytdlp_windows.ps1"
  if (Test-Path $dl) { & $dl }
}
$cid = "kimne78kx3ncx6brgo4mv6wki5h1ko"
$probeUrl = if ($TwitchClipOnly) { $TwitchClipUrl } else { $TwitchUrl }
Write-Log "yt-dlp probe url=$probeUrl"
$probeArgs = @(
  "--skip-download", "--print", "%(id)s|%(duration)s|%(title).80s",
  "--extractor-args", "twitch:client_id=$cid",
  $probeUrl
)
$probeOut = & $ytdlp @probeArgs 2>&1
$probeExit = $LASTEXITCODE
Write-Log "yt-dlp exit=$probeExit out=$($probeOut | Select-Object -First 8 | Out-String)"
if ($probeExit -eq 0 -and ("$probeOut" -match "\|")) {
  $result.ytdlp_probe_ok = $true
  $result.ytdlp_probe_detail = ("$probeOut" -split "`n" | Select-Object -First 1).Trim()
} else {
  $blob = ("$probeOut").ToLower()
  if ($blob -match "unavailable|not found|deleted|private|unpublished") {
    $result.ytdlp_probe_detail = "honest_unavailable: $probeOut"
  } else {
    $result.ytdlp_probe_detail = "probe_failed: $probeOut"
  }
}

$fixture = Ensure-Fixture
$config = (Resolve-Path (Join-Path $root "config\desktop.yaml")).Path
$ffmpegDir = Join-Path $root "bin\ffmpeg"
$ytdlpDir = Join-Path $root "bin\yt-dlp"
$env:PATH = "$ffmpegDir;$ytdlpDir;" + $env:PATH
# Force file SQLite under dataDir. Parent shells often leave pytest's
# STREAMCLIP_DATABASE__URL=sqlite+aiosqlite:///:memory: which wins over
# configure_data_dirs setdefault and 500s every /api/jobs call.
$dbPath = (Join-Path $dataDir "streamclip.db") -replace '\\', '/'
$env:STREAMCLIP_CONFIG = $config
$env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
$env:STREAMCLIP_DATABASE__URL = "sqlite+aiosqlite:///$dbPath"
$env:STREAMCLIP_DATABASE__SYNC_URL = "sqlite:///$dbPath"
$env:STREAMCLIP_STORAGE__LOCAL_ROOT = Join-Path $dataDir "storage"
$env:STREAMCLIP_WORKSPACE_DIR = Join-Path $dataDir "workspace"
$env:STREAMCLIP_CACHE_DIR = Join-Path $dataDir "cache"
$env:STREAMCLIP_OUTPUT_DIR = Join-Path $dataDir "output"
$env:STREAMCLIP_SIDECAR_PORT = "$Port"
$env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"
$env:STREAMCLIP_SIDECAR_SKIP_MIGRATE = "0"
$env:STREAMCLIP_WHISPER__MODEL_SIZE = "tiny"
$env:STREAMCLIP_WHISPER__DEVICE = "cpu"
$env:STREAMCLIP_WHISPER__COMPUTE_TYPE = "int8"
# Host/dev Python often lacks sentence_transformers; overlays are optional for
# ingest/Twitch proof. Packaged sidecar bundles the model dependency.
$env:STREAMCLIP_OVERLAY__ENABLED = "false"
Remove-Item Env:STREAMCLIP_SIDECAR_SKIP_MIGRATE -ErrorAction SilentlyContinue
$env:STREAMCLIP_SIDECAR_SKIP_MIGRATE = "0"

$headers = @{
  "Content-Type" = "application/json"
  "X-Device-Id"  = "smoke0123456789abcdef0123456789ab"
}
$base = "http://127.0.0.1:$Port"
$proc = $null
$logOut = Join-Path $dataDir "sidecar.out.log"
$logErr = Join-Path $dataDir "sidecar.err.log"

try {
  Write-Log "START python -m desktop_sidecar port=$Port data=$dataDir"
  $proc = Start-Process -FilePath "python" -ArgumentList @("-m", "desktop_sidecar") `
    -WorkingDirectory $root -PassThru -NoNewWindow `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr

  $healthy = $false
  for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) {
      Write-Log "FAIL sidecar exited code=$($proc.ExitCode)"
      if (Test-Path $logErr) { Get-Content $logErr -Tail 40 | ForEach-Object { Write-Log $_ } }
      throw "sidecar exited early"
    }
    try {
      $h = Invoke-RestMethod "$base/api/health" -TimeoutSec 3
      if ($h.status -eq "ok" -or $h.database) { $healthy = $true; break }
    } catch {}
  }
  if (-not $healthy) { throw "never healthy" }
  Write-Log "healthy"

  try {
    $null = Invoke-RestMethod -Method Post -Uri "$base/api/devices/onboarding-complete" -Headers $headers `
      -Body (@{ device_id = $headers["X-Device-Id"] } | ConvertTo-Json)
  } catch {}

  # --- UPLOAD full pipeline ---
  $bytes = [System.IO.File]::ReadAllBytes($fixture)
  $init = Invoke-RestMethod -Method Post -Uri "$base/api/uploads/init" -Headers $headers -Body (@{
      filename     = "smoke_video.mp4"
      content_type = "video/mp4"
      size_bytes   = $bytes.Length
    } | ConvertTo-Json)
  $putUrl = $init.upload_url
  if ($putUrl.StartsWith("/")) { $putUrl = "$base$putUrl" }
  Invoke-WebRequest -Method Put -Uri $putUrl -ContentType "video/mp4" -InFile $fixture -UseBasicParsing | Out-Null
  Write-Log "uploaded key=$($init.storage_key) bytes=$($bytes.Length)"

  $job = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" -Headers $headers -Body (@{
      source_upload_key = $init.storage_key
      target_clips      = 1
    } | ConvertTo-Json)
  $result.upload_job_id = $job.id
  Write-Log "upload job=$($job.id)"

  $deadline = (Get-Date).AddMinutes($UploadTimeoutMinutes)
  $last = ""
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if ($proc.HasExited) { throw "sidecar died mid-upload-job" }
    $j = Invoke-RestMethod "$base/api/jobs/$($job.id)" -Headers $headers
    $clipN = @($j.clips).Count
    $line = "upload status=$($j.status) stage=$($j.current_stage) progress=$($j.progress) clips=$clipN"
    if ($line -ne $last) { Write-Log $line; $last = $line }
    $result.upload_status = "$($j.status)"
    $result.upload_clips = $clipN
    $result.upload_error = "$($j.error_message)"
    if ($j.status -eq "error" -or $j.status -eq "failed" -or $j.error_code) {
      throw "upload job failed: $($j.error_code) $($j.error_message)"
    }
    if ($j.status -eq "done" -or $j.status -eq "completed") {
      if ($clipN -lt 1) { throw "upload done but clips=0" }
      Write-Log "PASS upload clips=$clipN"
      break
    }
  }
  if ($result.upload_status -notin @("done", "completed")) {
    throw "upload timeout last=$last"
  }

  $ingestPastDownload = $false
  $honestFail = $false
  if (-not $SkipTwitch) {
    $url = if ($TwitchClipOnly) { $TwitchClipUrl } else { $TwitchUrl }
    $result.twitch_mode = if ($TwitchClipOnly) { "clip" } else { "vod" }
    $tjob = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" -Headers $headers -Body (@{
        source_url   = $url
        target_clips = 1
      } | ConvertTo-Json)
    $result.twitch_job_id = $tjob.id
    Write-Log "twitch job=$($tjob.id) url=$url"
    $twitchStarted = Get-Date

    $deadline = (Get-Date).AddMinutes($TwitchTimeoutMinutes)
    $last = ""
    while ((Get-Date) -lt $deadline) {
      Start-Sleep -Seconds 5
      if ($proc.HasExited) { throw "sidecar died mid-twitch-job" }
      $j = Invoke-RestMethod "$base/api/jobs/$($tjob.id)" -Headers $headers
      $clipN = @($j.clips).Count
      $stage = "$($j.current_stage)"
      $line = "twitch status=$($j.status) stage=$stage progress=$($j.progress) clips=$clipN err=$($j.error_message)"
      if ($line -ne $last) { Write-Log $line; $last = $line }
      $result.twitch_status = "$($j.status)"
      $result.twitch_stage = $stage
      $result.twitch_clips = $clipN
      $result.twitch_error = "$($j.error_message)"

      $prog = 0.0
      try { $prog = [double]$j.progress } catch {}
      if ($stage -match "transcrib|highlight|virality|process_clip|final" -or $prog -gt 0.15) {
        $ingestPastDownload = $true
      }

      if ($j.status -eq "done" -or $j.status -eq "completed") {
        Write-Log "PASS twitch full clips=$clipN"
        break
      }
      if ($j.status -eq "error" -or $j.status -eq "failed" -or $j.error_code) {
        $msg = "$($j.error_message)".ToLower()
        if ($msg -match "downloadable vod|no longer available|unpublished|uploading again|channel or listing|isn't a downloadable") {
          $honestFail = $true
          Write-Log "twitch honest failure: $($j.error_message)"
          break
        }
        throw "twitch job failed: $($j.error_code) $($j.error_message)"
      }

      # Long VOD: accept ingest proof after 12m past download (full render deferred)
      $elapsed = ((Get-Date) - $twitchStarted).TotalMinutes
      if ($ingestPastDownload -and $elapsed -ge 12 -and $result.twitch_mode -eq "vod") {
        Write-Log "PASS-INGEST twitch long VOD deferred full pipeline (stage=$stage)"
        break
      }
    }
  } else {
    $result.twitch_status = "skipped"
  }

  # Strict ship gate: upload done+clips; Twitch done+clips (clip mode) OR
  # (VOD mode) ytdlp probe OK + (done+clips OR past-ingest OR honest unavailable).
  $uploadOk = ($result.upload_status -in @("done", "completed")) -and ($result.upload_clips -ge 1)
  $twitchFull = ($result.twitch_status -in @("done", "completed")) -and ($result.twitch_clips -ge 1)
  $twitchOk = $false
  if ($SkipTwitch) {
    $twitchOk = $false
  } elseif ($twitchFull) {
    $twitchOk = $true
  } elseif ($result.twitch_mode -eq "vod" -and $result.ytdlp_probe_ok -and ($ingestPastDownload -or $honestFail)) {
    $twitchOk = $true
  } elseif ($honestFail -and $result.ytdlp_probe_ok) {
    $twitchOk = $true
  }

  $result.overall_pass = [bool]($uploadOk -and $result.reject_ok -and $result.normalize_ok -and $result.ytdlp_probe_ok -and $twitchOk)
  Write-Log "SUMMARY overall_pass=$($result.overall_pass) upload=$($result.upload_status)/$($result.upload_clips) twitch=$($result.twitch_status)/$($result.twitch_stage)/$($result.twitch_clips) ytdlp=$($result.ytdlp_probe_ok)"
}
catch {
  Write-Log "FAIL exception: $($_.Exception.Message)"
  $result.overall_pass = $false
  if (-not $result.upload_error) { $result.upload_error = $_.Exception.Message }
}
finally {
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
  Remove-Item Env:STREAMCLIP_CONFIG, Env:STREAMCLIP_DESKTOP_DATA_DIR, Env:STREAMCLIP_SIDECAR_PORT,
    Env:STREAMCLIP_SIDECAR_SKIP_PREFETCH, Env:STREAMCLIP_WHISPER__MODEL_SIZE,
    Env:STREAMCLIP_WHISPER__DEVICE, Env:STREAMCLIP_WHISPER__COMPUTE_TYPE -ErrorAction SilentlyContinue
  ($result | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath $resultPath -Encoding utf8
  Write-Log "wrote $resultPath"
}

if (-not $result.overall_pass) { exit 1 }
exit 0
