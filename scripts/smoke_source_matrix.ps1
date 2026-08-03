# Packaged-sidecar source matrix smoke (install-like constraints).
# Pass = job status done. Unit tests do not count.
#
# Usage:
#   .\scripts\smoke_source_matrix.ps1 -Source upload-video
#   .\scripts\smoke_source_matrix.ps1 -Source youtube -MediumWhisper
#   .\scripts\smoke_source_matrix.ps1 -Source twitch-clip -SourceUrl "https://..."
#
# Sidecar resolution order:
#   1) -SidecarDir
#   2) apps/desktop/release/win-unpacked/resources/sidecar
#   3) %LOCALAPPDATA%\Programs\qClip\resources\sidecar
#   4) dist/streamclip-sidecar

param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    "upload-video",
    "upload-audio",
    "twitch-vod",
    "twitch-clip",
    "youtube",
    "youtube-watch",
    "kick",
    "tiktok",
    "direct-http"
  )]
  [string]$Source,

  [string]$SourceUrl = "",
  [string]$SidecarDir = "",
  [string]$FixtureVideo = "",
  [string]$FixtureAudio = "",
  [switch]$MediumWhisper,
  [int]$Port = 0,
  [int]$TimeoutMinutes = 25,
  [int]$TargetClips = 1
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Write-Log([string]$Message) {
  $line = "$(Get-Date -Format o) $Message"
  Write-Host $line
  if ($script:RunLog) { Add-Content -LiteralPath $script:RunLog -Value $line }
}

function Resolve-SidecarDir([string]$Override) {
  if ($Override) {
    $exe = Join-Path $Override "streamclip-sidecar.exe"
    if (-not (Test-Path -LiteralPath $exe)) { throw "Missing sidecar exe: $exe" }
    return (Resolve-Path -LiteralPath $Override).Path
  }
  $candidates = @(
    (Join-Path $root "apps\desktop\release\win-unpacked\resources\sidecar"),
    (Join-Path $env:LOCALAPPDATA "Programs\qClip\resources\sidecar"),
    (Join-Path $root "dist\streamclip-sidecar")
  )
  foreach ($c in $candidates) {
    if (Test-Path -LiteralPath (Join-Path $c "streamclip-sidecar.exe")) {
      return (Resolve-Path -LiteralPath $c).Path
    }
  }
  throw "No packaged sidecar found. Build/install first."
}

function Ensure-Fixtures {
  $fixDir = Join-Path $root "tmp\fixtures"
  New-Item -ItemType Directory -Path $fixDir -Force | Out-Null
  $ffCandidates = @(
    (Join-Path $script:SidecarDir "_internal\bin\ffmpeg\ffmpeg.exe"),
    (Join-Path $script:SidecarDir "bin\ffmpeg\ffmpeg.exe"),
    (Join-Path $root "bin\ffmpeg\ffmpeg.exe")
  )
  $ffmpeg = $ffCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
  if (-not $ffmpeg) { throw "ffmpeg not found for fixture generation" }

  $video = Join-Path $fixDir "smoke_video.mp4"
  if (-not (Test-Path -LiteralPath $video)) {
    Write-Log "Generating fixture video: $video"
    $ffLog = Join-Path $fixDir "ffmpeg-video.log"
    $ffArgs = @(
      "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30",
      "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
      "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", $video
    )
    $p = Start-Process -FilePath $ffmpeg -ArgumentList $ffArgs -Wait -PassThru -NoNewWindow `
      -RedirectStandardError $ffLog -RedirectStandardOutput (Join-Path $fixDir "ffmpeg-video-out.log")
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $video)) {
      throw "Failed to create $video (ffmpeg exit $($p.ExitCode)); see $ffLog"
    }
  }

  $audio = Join-Path $fixDir "smoke_audio.wav"
  if (-not (Test-Path -LiteralPath $audio)) {
    Write-Log "Generating fixture audio: $audio"
    $ffLog = Join-Path $fixDir "ffmpeg-audio.log"
    $ffArgs = @("-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "12", $audio)
    $p = Start-Process -FilePath $ffmpeg -ArgumentList $ffArgs -Wait -PassThru -NoNewWindow `
      -RedirectStandardError $ffLog -RedirectStandardOutput (Join-Path $fixDir "ffmpeg-audio-out.log")
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $audio)) {
      throw "Failed to create $audio (ffmpeg exit $($p.ExitCode)); see $ffLog"
    }
  }

  return @{ Video = $video; Audio = $audio; Ffmpeg = $ffmpeg }
}

function Get-DefaultUrl([string]$Kind) {
  switch ($Kind) {
    "youtube" { return "https://www.youtube.com/shorts/jNQXAC9IVRw" }
    "youtube-watch" { return "https://www.youtube.com/watch?v=jNQXAC9IVRw" }
    "twitch-clip" { return "https://www.twitch.tv/xqc/clip/StupidSavoryBunnyGOWSkull-UOULtimf_a-kocc0" }
    # Short public VODs expire; override with -SourceUrl when needed.
    "twitch-vod" { return "https://www.twitch.tv/videos/2322346547" }
    "kick" { return "https://kick.com/xqc/videos/78a39add-ac70-4c16-8fae-9eca007d1cc4" }
    "tiktok" { return "https://www.tiktok.com/@scout2015/video/6718339397690690821" }
    default { return "" }
  }
}

function Append-ResultRow([string]$SourceName, [string]$Status, [string]$Detail, [string]$LogPath) {
  $resultsDir = Join-Path $root "tmp\smoke_matrix"
  New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
  $resultsPath = Join-Path $resultsDir "RESULTS.md"
  if (-not (Test-Path -LiteralPath $resultsPath)) {
    @(
      "# Source matrix smoke results",
      "",
      "**Pass rule:** packaged sidecar only (cwd=sidecar, PATH scrubbed of repo bin/). Job must reach ``status=done``. Unit/mock tests do not count.",
      "",
      "| Timestamp (UTC) | Source | Status | Detail | Log |",
      "|-----------------|--------|--------|--------|-----|"
    ) | Set-Content -LiteralPath $resultsPath -Encoding utf8
  }
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $row = "| $ts | $SourceName | $Status | $Detail | ``$LogPath`` |"
  Add-Content -LiteralPath $resultsPath -Value $row
}

function Start-DirectHttpServer([string]$FilePath, [int]$ListenPort) {
  $serveDir = Join-Path $env:TEMP ("qclip-direct-http-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
  New-Item -ItemType Directory -Path $serveDir | Out-Null
  $served = Join-Path $serveDir "smoke_video.mp4"
  Copy-Item -LiteralPath $FilePath -Destination $served -Force
  $procHttp = Start-Process -FilePath "python" -ArgumentList @("-m", "http.server", "$ListenPort", "--bind", "127.0.0.1") `
    -WorkingDirectory $serveDir -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 1
  if ($procHttp.HasExited) { throw "direct-http server failed to start" }
  return @{
    Proc = $procHttp
    Url  = "http://127.0.0.1:$ListenPort/smoke_video.mp4"
    Dir  = $serveDir
  }
}

# ── resolve paths / ports ────────────────────────────────────────────────────
$script:SidecarDir = Resolve-SidecarDir $SidecarDir
$exe = Join-Path $script:SidecarDir "streamclip-sidecar.exe"
$fixtures = Ensure-Fixtures
if (-not $FixtureVideo) { $FixtureVideo = $fixtures.Video }
if (-not $FixtureAudio) { $FixtureAudio = $fixtures.Audio }

if ($Port -le 0) {
  $Port = 8820 + (Get-Random -Maximum 80)
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$resultsDir = Join-Path $root "tmp\smoke_matrix"
New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
$script:RunLog = Join-Path $resultsDir ("{0}-{1}.log" -f $Source, $stamp)

$dataDir = Join-Path $env:TEMP ("qclip-matrix-" + $Source + "-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $dataDir | Out-Null
$logOut = Join-Path $dataDir "out.log"
$logErr = Join-Path $dataDir "err.log"

$cleanPath = ($env:PATH -split ';' | Where-Object {
  $_ -and ($_ -notmatch '[\\/]streamclip[\\/]bin[\\/]') -and ($_ -notmatch '[\\/]Projects[\\/]streamclip[\\/]bin')
}) -join ';'

$env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
$env:STREAMCLIP_SIDECAR_PORT = "$Port"
$env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"
if ($MediumWhisper) {
  $env:STREAMCLIP_WHISPER__MODEL_SIZE = "medium"
} else {
  $env:STREAMCLIP_WHISPER__MODEL_SIZE = "tiny"
}
$env:STREAMCLIP_WHISPER__DEVICE = "cpu"
$env:STREAMCLIP_WHISPER__COMPUTE_TYPE = "int8"
$env:PATH = $cleanPath

$directHttp = $null
$headers = @{
  "Content-Type" = "application/json"
  "X-Device-Id"  = "smoke0123456789abcdef0123456789ab"
}
$base = "http://127.0.0.1:$Port"
$exitCode = 1
$proc = $null

Write-Log "START source=$Source sidecar=$script:SidecarDir port=$Port model=$($env:STREAMCLIP_WHISPER__MODEL_SIZE)"
Write-Log "dataDir=$dataDir runLog=$script:RunLog"

try {
  $proc = Start-Process -FilePath $exe -WorkingDirectory $script:SidecarDir -PassThru -NoNewWindow `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr

  $healthy = $false
  for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) {
      Write-Log "FAIL sidecar exited early code=$($proc.ExitCode)"
      if (Test-Path $logErr) { Get-Content $logErr -Tail 40 | ForEach-Object { Write-Log $_ } }
      Append-ResultRow $Source "Fail" "sidecar_exit_$($proc.ExitCode)" $script:RunLog
      exit 1
    }
    try {
      $h = Invoke-RestMethod "$base/api/health" -TimeoutSec 3
      if ($h.status -eq "ok" -or $h.database) { $healthy = $true; break }
    } catch {}
  }
  if (-not $healthy) {
    Write-Log "FAIL never healthy"
    Append-ResultRow $Source "Fail" "never_healthy" $script:RunLog
    exit 1
  }
  Write-Log "healthy"

  # Optional onboarding (idempotent)
  try {
    $null = Invoke-RestMethod -Method Post -Uri "$base/api/devices/onboarding-complete" -Headers $headers `
      -Body (@{ device_id = $headers["X-Device-Id"] } | ConvertTo-Json)
  } catch {}

  $jobBody = @{ target_clips = $TargetClips }

  switch ($Source) {
    "upload-video" {
      $bytes = [System.IO.File]::ReadAllBytes($FixtureVideo)
      $init = Invoke-RestMethod -Method Post -Uri "$base/api/uploads/init" -Headers $headers -Body (@{
          filename     = "smoke_video.mp4"
          content_type = "video/mp4"
          size_bytes   = $bytes.Length
        } | ConvertTo-Json)
      $putUrl = $init.upload_url
      if ($putUrl.StartsWith("/")) { $putUrl = "$base$putUrl" }
      Invoke-WebRequest -Method Put -Uri $putUrl -ContentType "video/mp4" -InFile $FixtureVideo -UseBasicParsing | Out-Null
      $jobBody.source_upload_key = $init.storage_key
      Write-Log "uploaded video key=$($init.storage_key) bytes=$($bytes.Length)"
    }
    "upload-audio" {
      $bytes = [System.IO.File]::ReadAllBytes($FixtureAudio)
      $init = Invoke-RestMethod -Method Post -Uri "$base/api/uploads/init" -Headers $headers -Body (@{
          filename     = "smoke_audio.wav"
          content_type = "audio/wav"
          size_bytes   = $bytes.Length
        } | ConvertTo-Json)
      $putUrl = $init.upload_url
      if ($putUrl.StartsWith("/")) { $putUrl = "$base$putUrl" }
      Invoke-WebRequest -Method Put -Uri $putUrl -ContentType "audio/wav" -InFile $FixtureAudio -UseBasicParsing | Out-Null
      $jobBody.source_upload_key = $init.storage_key
      Write-Log "uploaded audio key=$($init.storage_key) bytes=$($bytes.Length)"
    }
    "direct-http" {
      # normalize_source_url rewrites http:// -> https://, so loopback HTTP cannot work.
      # Product smoke uses a public HTTPS media URL (override with -SourceUrl).
      $url = $SourceUrl
      if (-not $url) {
        $url = "https://download.samplelib.com/mp4/sample-5s.mp4"
      }
      $jobBody.source_url = $url
      Write-Log "direct-http url=$url"
    }
    default {
      $url = $SourceUrl
      if (-not $url) { $url = Get-DefaultUrl $Source }
      if (-not $url) { throw "No URL for source $Source; pass -SourceUrl" }
      $jobBody.source_url = $url
      Write-Log "source_url=$url"
    }
  }

  $job = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" -Headers $headers -Body ($jobBody | ConvertTo-Json)
  $jobId = $job.id
  Write-Log "job=$jobId"

  $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
  $last = ""
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if ($proc.HasExited) { throw "sidecar died mid-job" }
    $j = Invoke-RestMethod "$base/api/jobs/$jobId" -Headers $headers
    $line = "status=$($j.status) stage=$($j.current_stage) progress=$($j.progress) err=$($j.error_code) clips=$(@($j.clips).Count)"
    if ($line -ne $last) { Write-Log $line; $last = $line }

    if ($j.error_code -or $j.status -eq "error" -or $j.status -eq "failed") {
      Write-Log "FAIL $($j.error_code) $($j.error_message)"
      Select-String -Path $logOut, $logErr -Pattern "failure|ModuleNotFound|audio_analyser|tracking_failed|virality|IngestError|NoAudio|slate" `
        -ErrorAction SilentlyContinue | Select-Object -Last 40 | ForEach-Object { Write-Log $_.Line }
      Append-ResultRow $Source "Fail" "$($j.error_code):$($j.error_message)" $script:RunLog
      $exitCode = 2
      exit $exitCode
    }

    if ($j.status -eq "done" -or $j.status -eq "completed") {
      $out = ""
      if (Test-Path $logOut) { $out = Get-Content $logOut -Raw -ErrorAction SilentlyContinue }
      if ($out -match "audio_analyser_failed") { Write-Log "WARN audio_analyser_failed logged" }
      if ($out -match "tracking_failed_fallback") { Write-Log "WARN tracking_failed_fallback logged" }
      if ($out -match "virality_ollama_unreachable") { Write-Log "INFO virality skipped (no Ollama)" }
      if ($out -match "loading_audio|audio_energy|slate") { Write-Log "INFO audio/slate path engaged" }
      Write-Log "PASS $Source job done clips=$(@($j.clips).Count)"
      Append-ResultRow $Source "Pass" "job=$jobId clips=$(@($j.clips).Count)" $script:RunLog
      $exitCode = 0
      exit $exitCode
    }
  }

  Write-Log "FAIL timeout after ${TimeoutMinutes}m last=$last"
  Append-ResultRow $Source "Fail" "timeout:$last" $script:RunLog
  $exitCode = 3
  exit $exitCode
}
catch {
  Write-Log "FAIL exception: $($_.Exception.Message)"
  Append-ResultRow $Source "Fail" $_.Exception.Message $script:RunLog
  $exitCode = 1
  exit $exitCode
}
finally {
  if ($directHttp) {
    if ($directHttp.Proc -and -not $directHttp.Proc.HasExited) {
      Stop-Process -Id $directHttp.Proc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($directHttp.Dir -and (Test-Path -LiteralPath $directHttp.Dir)) {
      Remove-Item -LiteralPath $directHttp.Dir -Recurse -Force -ErrorAction SilentlyContinue
    }
  }
  if ($proc -and -not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
  Remove-Item Env:STREAMCLIP_DESKTOP_DATA_DIR, Env:STREAMCLIP_SIDECAR_PORT, Env:STREAMCLIP_SIDECAR_SKIP_PREFETCH,
    Env:STREAMCLIP_WHISPER__MODEL_SIZE, Env:STREAMCLIP_WHISPER__DEVICE, Env:STREAMCLIP_WHISPER__COMPUTE_TYPE -ErrorAction SilentlyContinue
  Write-Log "artifacts dataDir=$dataDir runLog=$script:RunLog"
}
