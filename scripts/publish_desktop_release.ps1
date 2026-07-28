# Build Windows installer locally and optionally upload to GitHub Releases.
# Also uploads latest.yml (electron-updater) when present and bumps docs/GET_STARTED.md.
param(
    [string]$Version = "1.0.0-beta.5",
    [switch]$SkipBuild,
    [switch]$PublishOnly,
    [switch]$NoDocsBump
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$releaseDir = Join-Path $root "apps\desktop\release"
$installer = Join-Path $releaseDir "qClip-Setup-win-x64.exe"
$latestYml = Join-Path $releaseDir "latest.yml"

if (-not $PublishOnly -and -not $SkipBuild) {
    Write-Host "=== Building qClip Windows installer ===" -ForegroundColor Cyan
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
Write-Host "  https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe"
Write-Host ""
Write-Host "Docs page:" -ForegroundColor Cyan
Write-Host "  https://streamclip-henna.vercel.app/GET_STARTED/"
Write-Host ""

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI (gh) to publish, or upload manually:" -ForegroundColor Yellow
    Write-Host "  gh release create v$Version `"$installer`" --title `"qClip v$Version`""
    exit 0
}

$tag = "v$Version"
$assets = @($installer)
if (Test-Path $latestYml) { $assets += $latestYml }

Write-Host "Publishing release $tag ..." -ForegroundColor Cyan
$releaseNotes = @"
Windows 64-bit installer. SmartScreen may warn on unsigned beta builds - More info, Run anyway.

Docs: https://streamclip-henna.vercel.app/GET_STARTED/
"@

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
gh release view $tag 1>$null 2>$null
$releaseExists = $LASTEXITCODE -eq 0
$ErrorActionPreference = $prevEap

if ($releaseExists) {
    Write-Host "Release $tag exists - uploading assets with --clobber" -ForegroundColor Yellow
    gh release upload $tag @assets --clobber
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    gh release create $tag @assets `
        --title "qClip $tag" `
        --notes $releaseNotes `
        --latest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Release create failed. Retry upload: gh release upload $tag `"$installer`" --clobber" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

if (-not $NoDocsBump) {
    $docsPath = Join-Path $root "docs\GET_STARTED.md"
    if (Test-Path $docsPath) {
        $today = Get-Date -Format "yyyy-MM-dd"
        # UTF-8 safe bump via Python (PowerShell Set-Content corrupts emoji/emdash).
        $py = @"
from pathlib import Path
import re
p = Path(r'$docsPath')
text = p.read_text(encoding='utf-8')
version = '$Version'
pattern = r'(\*\*Current Windows build:\*\* `)[^`]+(` · `qClip-Setup-win-x64\.exe` \([^)]+\))'
if version in text:
    print('docs already mention version')
else:
    text2, n = re.subn(pattern, rf'\1{version}\2', text, count=1)
    if n:
        p.write_text(text2, encoding='utf-8', newline='')
        print('bumped GET_STARTED.md Windows build line')
    else:
        raise SystemExit('Current Windows build line not found in GET_STARTED.md')
"@
        $result = $py | python -
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "GET_STARTED.md: $result" -ForegroundColor Green
    }
}

Write-Host "Published. Download link is live on GET_STARTED.md." -ForegroundColor Green
