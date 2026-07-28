# Build Windows installer locally and optionally upload to GitHub Releases.
# Also uploads latest.yml (electron-updater) when present and bumps BETA_DOWNLOAD.md.
# Signing runbook: docs/DESKTOP_SIGNING.md
#
# Unsigned beta (current):  .\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N
# Signed gate:              .\scripts\publish_desktop_release.ps1 -Version ... -SkipBuild -RequireSigned
# No upload / no docs bump: .\scripts\publish_desktop_release.ps1 -Version ... -SkipBuild -DryRun
param(
    [string]$Version = "1.0.0-beta.4",
    [switch]$SkipBuild,
    [switch]$PublishOnly,
    [switch]$NoDocsBump,
    [switch]$RequireSigned,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$releaseDir = Join-Path $root "apps\desktop\release"
$installer = Join-Path $releaseDir "qClip-Setup-win-x64.exe"
$latestYml = Join-Path $releaseDir "latest.yml"

if (-not $PublishOnly -and -not $SkipBuild) {
    if ($DryRun) {
        Write-Host "Dry-run: would build via build_desktop_installer.ps1 (use -SkipBuild to inspect an existing exe)." -ForegroundColor Yellow
    } else {
        Write-Host "=== Building qClip Windows installer ===" -ForegroundColor Cyan
        & "$PSScriptRoot\build_desktop_installer.ps1"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} elseif ($SkipBuild -and -not $PublishOnly) {
    Write-Host "Skipping build (-SkipBuild); publishing existing installer if present." -ForegroundColor Yellow
}

if (-not (Test-Path $installer)) {
    Write-Error "Installer not found: $installer"
}

$mb = [math]::Round((Get-Item $installer).Length / 1MB)
$sigStatus = "Unknown"
$sigPublisher = ""
try {
    $sig = Get-AuthenticodeSignature -FilePath $installer
    $sigStatus = [string]$sig.Status
    if ($sig.SignerCertificate) {
        $sigPublisher = [string]$sig.SignerCertificate.Subject
    }
} catch {
    $sigStatus = "Unreadable"
}

$isSignedValid = $sigStatus -eq "Valid"
Write-Host ""
Write-Host "Installer ready ($mb MB):" -ForegroundColor Green
Write-Host "  $installer"
Write-Host ("  Authenticode: {0}{1}" -f $sigStatus, $(if ($sigPublisher) { " | $sigPublisher" } else { "" })) `
    -ForegroundColor $(if ($isSignedValid) { "Green" } else { "Yellow" })
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
Write-Host "  https://streamclip-henna.vercel.app/BETA_DOWNLOAD/"
Write-Host "Signing runbook: docs/DESKTOP_SIGNING.md"
Write-Host ""

if ($RequireSigned -and -not $isSignedValid) {
    Write-Error "RequireSigned set but Authenticode Status is '$sigStatus' (want Valid). See docs/DESKTOP_SIGNING.md Path B."
}

if ($DryRun) {
    Write-Host "=== Publish dry-run (no gh, no docs bump) ===" -ForegroundColor Cyan
    Write-Host ("Tag:            v{0}" -f $Version)
    Write-Host ("Path:           {0}" -f $(if ($isSignedValid) { "SIGNED" } else { "UNSIGNED (beta)" }))
    Write-Host ("RequireSigned:  {0}" -f $(if ($RequireSigned) { "yes" } else { "no" }))
    Write-Host ("NoDocsBump:     {0}" -f $(if ($NoDocsBump) { "yes" } else { "no (would bump BETA_DOWNLOAD.md)" }))
    Write-Host "Dry-run complete." -ForegroundColor Green
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Install GitHub CLI (gh) to publish, or upload manually:" -ForegroundColor Yellow
    Write-Host "  gh release create v$Version `"$installer`" --title `"qClip v$Version`""
    exit 0
}

$tag = "v$Version"
$assets = @($installer)
if (Test-Path $latestYml) { $assets += $latestYml }

if ($isSignedValid) {
    $releaseNotes = @"
Windows 64-bit installer (Authenticode signed). SmartScreen reputation may still warm up on early downloads.

Docs: https://streamclip-henna.vercel.app/BETA_DOWNLOAD/
Signing: docs/DESKTOP_SIGNING.md
"@
} else {
    $releaseNotes = @"
Windows 64-bit installer. SmartScreen may warn on unsigned beta builds - More info, Run anyway.

Docs: https://streamclip-henna.vercel.app/BETA_DOWNLOAD/
"@
}

Write-Host "Publishing release $tag ..." -ForegroundColor Cyan

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
    $docsPath = Join-Path $root "docs\BETA_DOWNLOAD.md"
    if (Test-Path $docsPath) {
        $today = Get-Date -Format "yyyy-MM-dd"
        # UTF-8 safe bump via Python (PowerShell Set-Content corrupts emoji/emdash).
        $py = @"
from pathlib import Path
p = Path(r'$docsPath')
text = p.read_text(encoding='utf-8')
version = '$Version'
if version in text:
    print('docs already mention version')
else:
    today = '$today'
    banner = f'> **Current Windows installer:** ``{version}`` ({today}) — [download Setup exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)\n'
    lines = text.splitlines(keepends=True)
    out = []
    done = False
    for line in lines:
        out.append(line)
        if not done and line.startswith('# Get qClip'):
            nl = '\r\n' if line.endswith('\r\n') else '\n'
            out.append(nl)
            out.append(banner.replace('\n', nl))
            out.append(nl)
            done = True
    if done:
        p.write_text(''.join(out), encoding='utf-8', newline='')
        print('bumped')
    else:
        raise SystemExit('title not found in BETA_DOWNLOAD.md')
"@
        $result = $py | python -
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "BETA_DOWNLOAD.md: $result" -ForegroundColor Green
    }
}

Write-Host "Published. Download link is live on BETA_DOWNLOAD.md." -ForegroundColor Green
