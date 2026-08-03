# Packaged-sidecar RENDER matrix smoke (aspect ratio x reframe x captions).
# Pass requires ALL of:
#   - job done + ffprobe WxH match catalog dims
#   - captions_done in sidecar log (style != none); no_words_in_clip_window is FAIL
#   - *_captioned.mp4 present
#   - ASS Fontname= matches style (needs sidecar that persists .ass) OR fontname= log field
#   - OS has the declared caption font installed
#   - tracking presets log crop_window=; P0-all requires gaming crop != irl crop
#   - same-AR scale path may log reframe_scale_only instead of crop_window
#
# Usage:
#   .\scripts\smoke_render_matrix.ps1 -Cell P0-gaming
#   .\scripts\smoke_render_matrix.ps1 -Cell P0-all
#
# Sidecar resolution matches smoke_source_matrix.ps1 (install-like PATH scrub).
# ASCII-only script (PowerShell mis-tokenizes em-dashes).

param(
  [ValidateSet(
    "P0-gaming",
    "P0-irl",
    "P0-landscape",
    "P0-all"
  )]
  [string]$Cell = "P0-all",

  [ValidateSet("9:16", "1:1", "4:5", "16:9", "2:3")]
  [string]$AspectRatio = "9:16",

  [ValidateSet(
    "fps_game", "moba", "battle_royale", "sports_action", "irl", "podcast",
    "presentation", "cinematic_wide", "music_performance", "auto"
  )]
  [string]$ReframePreset = "fps_game",

  [ValidateSet(
    "gaming_impact", "shorts_bold", "tiktok_pop", "karaoke_highlight",
    "minimal_white", "podcast_clean", "accessibility_clean", "none"
  )]
  [string]$CaptionStyle = "gaming_impact",

  [ValidateSet(
    "gaming", "esports", "irl", "vlog", "podcast", "education", "sports", "music", "general"
  )]
  [string]$ContentProfile = "gaming",

  [string]$SidecarDir = "",
  [string]$FixtureVideo = "",
  [switch]$MediumWhisper,
  [switch]$SkipFontInstallCheck,
  [int]$Port = 0,
  [int]$TimeoutMinutes = 25,
  [int]$TargetClips = 1
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ExpectedDims = @{
  "9:16" = @(1080, 1920)
  "1:1"  = @(1080, 1080)
  "4:5"  = @(1080, 1350)
  "16:9" = @(1920, 1080)
  "2:3"  = @(1080, 1620)
}

# Preferred fonts from core/captions.py _STYLES, plus Windows-safe fallbacks
# from _FONT_FALLBACK_CHAINS (first installed wins at burn time).
$ExpectedCaptionFonts = @{
  "gaming_impact"       = @("Impact")
  "tiktok_pop"          = @("Arial Rounded MT Bold", "Arial Black", "Arial", "Impact")
  "minimal_white"       = @("Helvetica Neue", "Arial", "Calibri", "Segoe UI")
  "podcast_clean"       = @("SF Pro Display", "Segoe UI", "Arial", "Calibri")
  "shorts_bold"         = @("Impact")
  "karaoke_highlight"   = @("Arial Black", "Arial")
  "accessibility_clean" = @("Arial")
}

$P0Cells = @{
  "P0-gaming"    = @{ AspectRatio = "9:16"; ReframePreset = "fps_game"; CaptionStyle = "gaming_impact"; ContentProfile = "gaming" }
  "P0-irl"       = @{ AspectRatio = "9:16"; ReframePreset = "irl"; CaptionStyle = "shorts_bold"; ContentProfile = "irl" }
  "P0-landscape" = @{ AspectRatio = "16:9"; ReframePreset = "cinematic_wide"; CaptionStyle = "minimal_white"; ContentProfile = "vlog" }
}

$script:CellEvidence = @{}

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

function Test-FontInstalled([string]$FontName) {
  Add-Type -AssemblyName System.Drawing -ErrorAction Stop
  $col = New-Object System.Drawing.Text.InstalledFontCollection
  $names = @($col.Families | ForEach-Object { $_.Name })
  if ($names -contains $FontName) { return $true }
  # GDI family names sometimes drop the weight suffix.
  $base = ($FontName -replace '\s+(Bold|Regular|Black|Light)$', '').Trim()
  if ($base -and ($names -contains $base)) { return $true }
  return $false
}

function Ensure-FixtureVideo {
  $fixDir = Join-Path $root "tmp\fixtures"
  New-Item -ItemType Directory -Path $fixDir -Force | Out-Null
  $ffCandidates = @(
    (Join-Path $script:SidecarDir "_internal\bin\ffmpeg\ffmpeg.exe"),
    (Join-Path $script:SidecarDir "bin\ffmpeg\ffmpeg.exe"),
    (Join-Path $root "bin\ffmpeg\ffmpeg.exe")
  )
  $ffmpeg = $ffCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
  if (-not $ffmpeg) { throw "ffmpeg not found for fixture generation" }

  # Speech-bearing fixture (sine-only made prior P0 Pass a false positive: no_words).
  $video = Join-Path $fixDir "smoke_render_source_speech.mp4"
  if (-not (Test-Path -LiteralPath $video)) {
    Write-Log "Generating speech render fixture: $video"
    $wav = Join-Path $fixDir "smoke_render_speech.wav"
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
      $synth.Rate = 0
      $synth.SetOutputToWaveFile($wav)
      $synth.Speak("Wow what a clutch play. This highlight is insane. Let's go team. Unbelievable moment right there.")
    } finally {
      $synth.Dispose()
    }
    if (-not (Test-Path -LiteralPath $wav) -or ((Get-Item $wav).Length -lt 1000)) {
      throw "SAPI speech wav missing/empty: $wav"
    }
    $ffLog = Join-Path $fixDir "ffmpeg-render-fixture-speech.log"
    $ffArgs = @(
      "-y", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
      "-i", $wav,
      "-t", "14", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", $video
    )
    $p = Start-Process -FilePath $ffmpeg -ArgumentList $ffArgs -Wait -PassThru -NoNewWindow `
      -RedirectStandardError $ffLog -RedirectStandardOutput (Join-Path $fixDir "ffmpeg-render-fixture-speech-out.log")
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $video)) {
      throw "Failed to create $video (ffmpeg exit $($p.ExitCode)); see $ffLog"
    }
  }
  return @{ Video = $video; Ffmpeg = $ffmpeg }
}

function Resolve-Ffprobe([string]$FfmpegPath) {
  $dir = Split-Path -Parent $FfmpegPath
  $probe = Join-Path $dir "ffprobe.exe"
  if (Test-Path -LiteralPath $probe) { return $probe }
  $probe = Join-Path $dir "ffprobe"
  if (Test-Path -LiteralPath $probe) { return $probe }
  throw "ffprobe not found beside $FfmpegPath"
}

function Append-ResultRow([string]$CellName, [string]$Status, [string]$Detail, [string]$LogPath) {
  $resultsDir = Join-Path $root "tmp\smoke_render_matrix"
  New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
  $resultsPath = Join-Path $resultsDir "RESULTS.md"
  if (-not (Test-Path -LiteralPath $resultsPath)) {
    @(
      "# Render matrix smoke results",
      "",
      "**Pass rule:** packaged sidecar. Job done + dims + captions_done + Fontname/ASS + crop diverge (P0-all) + OS font installed.",
      "",
      "| Timestamp (UTC) | Cell | Status | Detail | Log |",
      "|-----------------|------|--------|--------|-----|"
    ) | Set-Content -LiteralPath $resultsPath -Encoding utf8
  }
  $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  Add-Content -LiteralPath $resultsPath -Value "| $ts | $CellName | $Status | $Detail | ``$LogPath`` |"
}

function Get-SidecarLogText([string]$LogOut, [string]$LogErr) {
  $parts = @()
  if (Test-Path -LiteralPath $LogOut) { $parts += (Get-Content -LiteralPath $LogOut -Raw -ErrorAction SilentlyContinue) }
  if (Test-Path -LiteralPath $LogErr) { $parts += (Get-Content -LiteralPath $LogErr -Raw -ErrorAction SilentlyContinue) }
  return ($parts -join "`n")
}

function Invoke-RenderCell {
  param(
    [string]$Label,
    [string]$Aspect,
    [string]$Preset,
    [string]$Caption,
    [string]$Profile,
    [int]$ListenPort
  )

  $cellId = "$Aspect|$Preset|$Caption"
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $safeLabel = ($Label -replace '[^a-zA-Z0-9_-]', '_')
  $resultsDir = Join-Path $root "tmp\smoke_render_matrix"
  New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
  $script:RunLog = Join-Path $resultsDir ("{0}-{1}.log" -f $safeLabel, $stamp)

  $dataDir = Join-Path $env:TEMP ("qclip-render-" + $safeLabel + "-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
  New-Item -ItemType Directory -Path $dataDir | Out-Null
  $logOut = Join-Path $dataDir "out.log"
  $logErr = Join-Path $dataDir "err.log"

  $cleanPath = ($env:PATH -split ';' | Where-Object {
    $_ -and ($_ -notmatch '[\\/]streamclip[\\/]bin[\\/]') -and ($_ -notmatch '[\\/]Projects[\\/]streamclip[\\/]bin')
  }) -join ';'

  $env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
  $env:STREAMCLIP_SIDECAR_PORT = "$ListenPort"
  $env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"
  if ($MediumWhisper) {
    $env:STREAMCLIP_WHISPER__MODEL_SIZE = "medium"
  } else {
    $env:STREAMCLIP_WHISPER__MODEL_SIZE = "tiny"
  }
  $env:STREAMCLIP_WHISPER__DEVICE = "cpu"
  $env:STREAMCLIP_WHISPER__COMPUTE_TYPE = "int8"
  $env:PATH = $cleanPath

  $exe = Join-Path $script:SidecarDir "streamclip-sidecar.exe"
  $headers = @{
    "Content-Type" = "application/json"
    "X-Device-Id"  = "smoke0123456789abcdef0123456789ab"
  }
  $base = "http://127.0.0.1:$ListenPort"
  $proc = $null

  Write-Log "START cell=$Label $cellId profile=$Profile port=$ListenPort model=$($env:STREAMCLIP_WHISPER__MODEL_SIZE)"
  Write-Log "dataDir=$dataDir runLog=$script:RunLog"

  try {
    if ($Caption -ne "none") {
      $fontCandidates = @($ExpectedCaptionFonts[$Caption])
      if ($fontCandidates.Count -eq 0) { throw "No expected font mapping for caption style $Caption" }
      if (-not $SkipFontInstallCheck) {
        $installed = $null
        foreach ($cand in $fontCandidates) {
          if (Test-FontInstalled $cand) { $installed = $cand; break }
        }
        if (-not $installed) {
          Write-Log "FAIL OS missing all caption fonts for style=$Caption candidates=$($fontCandidates -join ',')"
          Append-ResultRow $cellId "Fail" "font_missing:$($fontCandidates[0])" $script:RunLog
          return 2
        }
        Write-Log "INFO OS has font '$installed' (style=$Caption)"
      }
    }

    $proc = Start-Process -FilePath $exe -WorkingDirectory $script:SidecarDir -PassThru -NoNewWindow `
      -RedirectStandardOutput $logOut -RedirectStandardError $logErr

    $healthy = $false
    for ($i = 0; $i -lt 90; $i++) {
      Start-Sleep -Seconds 2
      if ($proc.HasExited) {
        Write-Log "FAIL sidecar exited early code=$($proc.ExitCode)"
        Append-ResultRow $cellId "Fail" "sidecar_exit_$($proc.ExitCode)" $script:RunLog
        return 1
      }
      try {
        $h = Invoke-RestMethod "$base/api/health" -TimeoutSec 3
        if ($h.status -eq "ok" -or $h.database) { $healthy = $true; break }
      } catch {}
    }
    if (-not $healthy) {
      Write-Log "FAIL never healthy"
      Append-ResultRow $cellId "Fail" "never_healthy" $script:RunLog
      return 1
    }
    Write-Log "healthy"

    try {
      $null = Invoke-RestMethod -Method Post -Uri "$base/api/devices/onboarding-complete" -Headers $headers `
        -Body (@{ device_id = $headers["X-Device-Id"] } | ConvertTo-Json)
    } catch {}

    $bytes = [System.IO.File]::ReadAllBytes($script:FixtureVideo)
    $init = Invoke-RestMethod -Method Post -Uri "$base/api/uploads/init" -Headers $headers -Body (@{
        filename     = "smoke_render_source_speech.mp4"
        content_type = "video/mp4"
        size_bytes   = $bytes.Length
      } | ConvertTo-Json)
    $putUrl = $init.upload_url
    if ($putUrl.StartsWith("/")) { $putUrl = "$base$putUrl" }
    Invoke-WebRequest -Method Put -Uri $putUrl -ContentType "video/mp4" -InFile $script:FixtureVideo -UseBasicParsing | Out-Null
    Write-Log "uploaded key=$($init.storage_key)"

    $jobBody = @{
      source_upload_key = $init.storage_key
      target_clips      = $TargetClips
      aspect_ratio      = $Aspect
      reframe_preset    = $Preset
      caption_style     = $Caption
      content_profile   = $Profile
    }
    $job = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" -Headers $headers -Body ($jobBody | ConvertTo-Json)
    $jobId = $job.id
    Write-Log "job=$jobId"

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $last = ""
    $j = $null
    while ((Get-Date) -lt $deadline) {
      Start-Sleep -Seconds 5
      if ($proc.HasExited) { throw "sidecar died mid-job" }
      $j = Invoke-RestMethod "$base/api/jobs/$jobId" -Headers $headers
      $line = "status=$($j.status) stage=$($j.current_stage) progress=$($j.progress) err=$($j.error_code) clips=$(@($j.clips).Count)"
      if ($line -ne $last) { Write-Log $line; $last = $line }

      if ($j.error_code -or $j.status -eq "error" -or $j.status -eq "failed") {
        Write-Log "FAIL $($j.error_code) $($j.error_message)"
        Append-ResultRow $cellId "Fail" "$($j.error_code):$($j.error_message)" $script:RunLog
        return 2
      }
      if ($j.status -eq "done" -or $j.status -eq "completed") { break }
    }

    if (-not $j -or ($j.status -ne "done" -and $j.status -ne "completed")) {
      Write-Log "FAIL timeout after ${TimeoutMinutes}m last=$last"
      Append-ResultRow $cellId "Fail" "timeout:$last" $script:RunLog
      return 3
    }

    $clip = @($j.clips) | Where-Object { $_.status -eq "done" -and $_.download_url } | Select-Object -First 1
    if (-not $clip) { $clip = @($j.clips) | Select-Object -First 1 }
    if (-not $clip) {
      Write-Log "FAIL no clips on done job"
      Append-ResultRow $cellId "Fail" "no_clips" $script:RunLog
      return 2
    }

    $downloadRel = $clip.download_url
    if (-not $downloadRel) {
      Write-Log "FAIL clip missing download_url id=$($clip.id)"
      Append-ResultRow $cellId "Fail" "missing_download_url" $script:RunLog
      return 2
    }
    if ($downloadRel.StartsWith("/")) { $downloadRel = "$base$downloadRel" }

    $outMp4 = Join-Path $dataDir ("clip-" + $clip.id + ".mp4")
    Invoke-WebRequest -Uri $downloadRel -OutFile $outMp4 -UseBasicParsing
    if (-not (Test-Path -LiteralPath $outMp4) -or ((Get-Item $outMp4).Length -lt 1000)) {
      Write-Log "FAIL downloaded clip empty/missing"
      Append-ResultRow $cellId "Fail" "empty_download" $script:RunLog
      return 2
    }

    $probeJsonPath = Join-Path $dataDir "ffprobe.json"
    $probeArgs = @(
      "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "v:0", $outMp4
    )
    $pp = Start-Process -FilePath $script:Ffprobe -ArgumentList $probeArgs -Wait -PassThru -NoNewWindow `
      -RedirectStandardOutput $probeJsonPath -RedirectStandardError (Join-Path $dataDir "ffprobe.err")
    if ($pp.ExitCode -ne 0) {
      Write-Log "FAIL ffprobe exit $($pp.ExitCode)"
      Append-ResultRow $cellId "Fail" "ffprobe_exit_$($pp.ExitCode)" $script:RunLog
      return 2
    }
    $probe = Get-Content $probeJsonPath -Raw | ConvertFrom-Json
    $stream = $probe.streams | Select-Object -First 1
    $gotW = [int]$stream.width
    $gotH = [int]$stream.height
    $exp = $ExpectedDims[$Aspect]
    $expW = [int]$exp[0]
    $expH = [int]$exp[1]
    Write-Log "ffprobe ${gotW}x${gotH} expected ${expW}x${expH}"
    if ($gotW -ne $expW -or $gotH -ne $expH) {
      Write-Log "FAIL dimension mismatch"
      Append-ResultRow $cellId "Fail" "dims ${gotW}x${gotH}!=${expW}x${expH}" $script:RunLog
      return 2
    }

    $sidecarLog = Get-SidecarLogText $logOut $logErr

    # Reframe evidence
    $cropWindow = $null
    if ($sidecarLog -match 'crop_window=([0-9]+x[0-9]+)') {
      $cropWindow = $Matches[1]
      Write-Log "INFO crop_window=$cropWindow"
    }
    $scaleOnly = ($sidecarLog -match 'reframe_scale_only')
    if ($scaleOnly) { Write-Log "INFO reframe_scale_only" }
    if ($sidecarLog -match 'boxblur') {
      Write-Log "FAIL unexpected boxblur in default process_clip path"
      Append-ResultRow $cellId "Fail" "unexpected_boxblur" $script:RunLog
      return 2
    }
    if ($sidecarLog -match 'letterbox') {
      Write-Log "FAIL unexpected letterbox marker in sidecar log"
      Append-ResultRow $cellId "Fail" "unexpected_letterbox" $script:RunLog
      return 2
    }
    # Same-AR sources may scale-only; otherwise require crop_window from tracking.
    if (-not $cropWindow -and -not $scaleOnly) {
      Write-Log "FAIL missing reframe_start crop_window and reframe_scale_only"
      Append-ResultRow $cellId "Fail" "no_reframe_evidence" $script:RunLog
      return 2
    }

    if ($Caption -ne "none") {
      if ($sidecarLog -match 'no_words_in_clip_window') {
        Write-Log "FAIL no_words_in_clip_window (caption burn skipped; fixture/transcript gap)"
        Append-ResultRow $cellId "Fail" "no_words_in_clip_window" $script:RunLog
        return 2
      }
      if ($sidecarLog -notmatch 'captions_done') {
        Write-Log "FAIL missing captions_done in sidecar log"
        Append-ResultRow $cellId "Fail" "missing_captions_done" $script:RunLog
        return 2
      }
      Write-Log "INFO captions_done present"

      $captionHits = @(
        Get-ChildItem -LiteralPath $dataDir -Recurse -Filter "*_captioned.mp4" -ErrorAction SilentlyContinue
      )
      if ($captionHits.Count -eq 0) {
        Write-Log "FAIL missing *_captioned.mp4 under dataDir"
        Append-ResultRow $cellId "Fail" "missing_captioned_mp4" $script:RunLog
        return 2
      }
      Write-Log "INFO captioned artifact: $($captionHits[0].FullName)"

      $fontCandidates = @($ExpectedCaptionFonts[$Caption])
      $assHits = @(
        Get-ChildItem -LiteralPath $dataDir -Recurse -Filter "*_captioned.ass" -ErrorAction SilentlyContinue
      )
      $matchedFont = $null
      if ($assHits.Count -gt 0) {
        $assText = Get-Content -LiteralPath $assHits[0].FullName -Raw
        foreach ($cand in $fontCandidates) {
          if ($assText -match [regex]::Escape(",$cand,")) { $matchedFont = $cand; break }
        }
        if (-not $matchedFont) {
          Write-Log "FAIL ASS Fontname not in candidates ($($fontCandidates -join ',')) file=$($assHits[0].FullName)"
          Append-ResultRow $cellId "Fail" "ass_fontname_mismatch" $script:RunLog
          return 2
        }
        Write-Log "INFO ASS Fontname=$matchedFont ($($assHits[0].Name))"
      } else {
        foreach ($cand in $fontCandidates) {
          if ($sidecarLog -match ("fontname[=:][`"']?" + [regex]::Escape($cand))) {
            $matchedFont = $cand
            break
          }
        }
        if ($matchedFont) {
          Write-Log "INFO captions_done fontname=$matchedFont from log (ASS not persisted; rebuild sidecar recommended)"
        } else {
          Write-Log "FAIL no *_captioned.ass and no fontname= in candidates ($($fontCandidates -join ','))"
          Append-ResultRow $cellId "Fail" "ass_not_persisted:$($fontCandidates[0])" $script:RunLog
          return 2
        }
      }
    } else {
      Write-Log "INFO caption style=none - skip caption asserts"
    }

    $script:CellEvidence[$Label] = @{
      CropWindow = $cropWindow
      ScaleOnly  = $scaleOnly
      Aspect     = $Aspect
      Preset     = $Preset
      Caption    = $Caption
    }

    $detail = "job=$jobId dims=${gotW}x${gotH}"
    if ($cropWindow) { $detail += " crop=$cropWindow" }
    if ($scaleOnly) { $detail += " scale_only" }
    Write-Log "PASS $Label $cellId $detail"
    Append-ResultRow $cellId "Pass" $detail $script:RunLog
    return 0
  }
  catch {
    Write-Log "FAIL exception: $($_.Exception.Message)"
    Append-ResultRow $cellId "Fail" $_.Exception.Message $script:RunLog
    return 1
  }
  finally {
    if ($proc -and -not $proc.HasExited) {
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:STREAMCLIP_DESKTOP_DATA_DIR, Env:STREAMCLIP_SIDECAR_PORT, Env:STREAMCLIP_SIDECAR_SKIP_PREFETCH,
      Env:STREAMCLIP_WHISPER__MODEL_SIZE, Env:STREAMCLIP_WHISPER__DEVICE, Env:STREAMCLIP_WHISPER__COMPUTE_TYPE -ErrorAction SilentlyContinue
    Write-Log "artifacts dataDir=$dataDir runLog=$script:RunLog"
  }
}

# -- resolve ------------------------------------------------------------------
$script:SidecarDir = Resolve-SidecarDir $SidecarDir
$fixtures = Ensure-FixtureVideo
if (-not $FixtureVideo) { $FixtureVideo = $fixtures.Video }
$script:FixtureVideo = $FixtureVideo
$script:Ffprobe = Resolve-Ffprobe $fixtures.Ffmpeg

if ($Port -le 0) {
  $Port = 8840 + (Get-Random -Maximum 40)
}

$cellsToRun = @()
if ($Cell -eq "P0-all") {
  foreach ($name in @("P0-gaming", "P0-irl", "P0-landscape")) {
    $cfg = $P0Cells[$name]
    $cellsToRun += [pscustomobject]@{
      Label = $name; AspectRatio = $cfg.AspectRatio; ReframePreset = $cfg.ReframePreset
      CaptionStyle = $cfg.CaptionStyle; ContentProfile = $cfg.ContentProfile
    }
  }
}
elseif ($Cell -and $P0Cells.ContainsKey($Cell)) {
  $cfg = $P0Cells[$Cell]
  $cellsToRun += [pscustomobject]@{
    Label = $Cell; AspectRatio = $cfg.AspectRatio; ReframePreset = $cfg.ReframePreset
    CaptionStyle = $cfg.CaptionStyle; ContentProfile = $cfg.ContentProfile
  }
}
else {
  $label = "custom-$AspectRatio-$ReframePreset-$CaptionStyle"
  $cellsToRun += [pscustomobject]@{
    Label = $label; AspectRatio = $AspectRatio; ReframePreset = $ReframePreset
    CaptionStyle = $CaptionStyle; ContentProfile = $ContentProfile
  }
}

$overall = 0
$portCursor = $Port
foreach ($c in $cellsToRun) {
  $rc = Invoke-RenderCell -Label $c.Label -Aspect $c.AspectRatio -Preset $c.ReframePreset `
    -Caption $c.CaptionStyle -Profile $c.ContentProfile -ListenPort $portCursor
  if ($rc -ne 0) { $overall = $rc }
  $portCursor += 1
}

# Cross-cell: fps_game vs irl must produce different crop windows on same fixture/AR.
if ($Cell -eq "P0-all" -and $overall -eq 0) {
  $g = $script:CellEvidence["P0-gaming"]
  $i = $script:CellEvidence["P0-irl"]
  if (-not $g -or -not $i -or -not $g.CropWindow -or -not $i.CropWindow) {
    Write-Host "$(Get-Date -Format o) FAIL P0-all missing crop_window evidence for gaming/irl diverge check"
    Append-ResultRow "P0-all-diverge" "Fail" "missing_crop_evidence" "(matrix)"
    $overall = 2
  } elseif ($g.CropWindow -eq $i.CropWindow) {
    Write-Host "$(Get-Date -Format o) FAIL P0-all crop_window identical gaming=$($g.CropWindow) irl=$($i.CropWindow) (presets not diverging)"
    Append-ResultRow "P0-all-diverge" "Fail" "crop_identical:$($g.CropWindow)" "(matrix)"
    $overall = 2
  } else {
    Write-Host "$(Get-Date -Format o) PASS P0-all crop diverge gaming=$($g.CropWindow) irl=$($i.CropWindow)"
    Append-ResultRow "P0-all-diverge" "Pass" "gaming=$($g.CropWindow) irl=$($i.CropWindow)" "(matrix)"
  }
}

exit $overall
