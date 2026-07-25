# Build Windows installer locally and optionally upload to GitHub Releases.
# Also uploads latest.yml (electron-updater) when present and bumps BETA_DOWNLOAD.md.
param(
    [string]$Version = "1.0.0-beta.4",
    [switch]$SkipBuild,
    [switch]$PublishOnly,
    [switch]$NoDocsBump
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$releaseDir = Join-Path $root "apps\desktop\release"
$installer = Join-Path $releaseDir "StreamClip-Setup-win-x64.exe"
$latestYml = Join-Path $releaseDir "latest.yml"

if (-not $PublishOnly -and -not $SkipBuild) {
    Write-Host "=== Building StreamClip Windows installer ===" -ForegroundColor Cyan
    & "$PSScriptRoot\build_desktop_installer.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} elseif ($SkipBuild -and -not $PublishOnly) {
    Write-Host "Skipping build (-SkipBuild); publishing existing installer if present." -ForegroundColor Yellow
}

if (-not (Test-Path $installer)) {
    Write-Error "Installer not found: $installer"
}

$mb = [math]::Round((Get-Item $installer).Length / 1MB)
Write-Host ""
Write-Host "Installer ready ($mb MB):" -ForegroundColor Green
Write-Host "  $installer"
if (Test-Path $latestYml) {
    Write-Host "  $latestYml"
} else {
    Write-Host "WARNING: latest.yml missing - electron-updater auto-update metadata will not ship." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Stable download URL (after GitHub Release publish):" -ForegroundColor Cyan
Write-Host "  https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe"
Write-Host ""
Write-Host "Docs page:" -ForegroundColor Cyan
Write-Host "  https://streamclip-henna.vercel.app/BETA_DOWNLOAD/"
Write-Host ""

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI (gh) to publish, or upload manually:" -ForegroundColor Yellow
    Write-Host "  gh release create v$Version `"$installer`" --title `"StreamClip v$Version`""
    exit 0
}

$tag = "v$Version"
$assets = @($installer)
if (Test-Path $latestYml) { $assets += $latestYml }

Write-Host "Publishing release $tag ..." -ForegroundColor Cyan
$releaseNotes = @"
Windows 64-bit installer. SmartScreen may warn on unsigned beta builds - More info, Run anyway.

Docs: https://streamclip-henna.vercel.app/BETA_DOWNLOAD/
"@

$existing = gh release view $tag 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
    Write-Host "Release $tag exists - uploading assets with --clobber" -ForegroundColor Yellow
    gh release upload $tag @assets --clobber
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    gh release create $tag @assets `
        --title "StreamClip $tag" `
        --notes $releaseNotes `
        --latest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Release create failed. Retry upload: gh release upload $tag `"$installer`" --clobber" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

if (-not $NoDocsBump) {
    $docsPath = Join-Path $root "docs\BETA_DOWNLOAD.md"
    if (Test-Path $docsPath) {
        $today = Get-Date -Format "yyyy-MM-dd"
        $raw = Get-Content $docsPath -Raw
        if ($raw -notmatch [regex]::Escape($Version)) {
            $download = "https://github.com/WheresWellium/StreamClip/releases/latest/download/StreamClip-Setup-win-x64.exe"
            $bannerLine = "> **Current Windows installer:** ``$Version`` ($today) - [download Setup exe]($download)"
            $marker = "# Get StreamClip"
            $idx = $raw.IndexOf($marker)
            if ($idx -ge 0) {
                $lineEnd = $raw.IndexOf("`n", $idx)
                if ($lineEnd -lt 0) { $lineEnd = $raw.Length - 1 }
                $insertAt = $lineEnd + 1
                $raw = $raw.Substring(0, $insertAt) + "`n" + $bannerLine + "`n" + $raw.Substring($insertAt)
            } else {
                $raw = $bannerLine + "`n`n" + $raw
            }
            Set-Content -Path $docsPath -Value $raw -Encoding utf8 -NoNewline
            Write-Host "Bumped docs/BETA_DOWNLOAD.md to $Version" -ForegroundColor Green
        }
    }
}

Write-Host "Published. Download link is live on BETA_DOWNLOAD.md." -ForegroundColor Green
