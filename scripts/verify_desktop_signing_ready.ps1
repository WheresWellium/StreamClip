# Preflight for Windows EV / Authenticode signing (§4.10).
# Fails closed when -RequireSigning and CSC_* are missing; otherwise reports status.
param(
    [switch]$RequireSigning,
    [string]$CertificatePath = $env:CSC_LINK,
    [string]$CertificatePassword = $env:CSC_KEY_PASSWORD,
    [string]$SignTool = $env:SIGNTOOL
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Test-SigningConfigured {
    return [bool]$CertificatePath -and [bool]$CertificatePassword
}

function Test-CertificateResolvable {
    if (-not $CertificatePath) { return $false }
    if (Test-Path -LiteralPath $CertificatePath) { return $true }
    # CI often stores base64 PFX in CSC_LINK
    if ($CertificatePath.Length -gt 256) { return $true }
    return $false
}

$warnings = @()
$errors = @()

if (-not (Test-SigningConfigured)) {
    if ($RequireSigning) {
        $errors += "CSC_LINK and CSC_KEY_PASSWORD required for signed release (set GitHub secrets WINDOWS_CSC_LINK / WINDOWS_CSC_KEY_PASSWORD in CI)"
    } else {
        $warnings += "CSC_LINK / CSC_KEY_PASSWORD unset - installer will be UNSIGNED (SmartScreen warning)"
    }
} else {
    if (-not (Test-CertificateResolvable)) {
        $errors += "CSC_LINK is not a readable file path and does not look like base64 PFX content"
    }
    if (-not $SignTool) {
        $kitsRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
        if (Test-Path $kitsRoot) {
            $SignTool = Get-ChildItem $kitsRoot -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match "\\x64\\" } |
                Sort-Object FullName -Descending |
                Select-Object -First 1 -ExpandProperty FullName
        }
    }
    if (-not $SignTool -or -not (Test-Path $SignTool)) {
        $warnings += "signtool.exe not found locally - electron-builder may still sign via winCodeSign; set SIGNTOOL for manual sign_windows_artifact.ps1"
    } else {
        Write-Host "signtool: $SignTool" -ForegroundColor DarkGray
    }
}

foreach ($w in $warnings) {
    Write-Host "WARN  $w" -ForegroundColor Yellow
}
foreach ($e in $errors) {
    Write-Host "FAIL  $e" -ForegroundColor Red
}

if ($errors.Count -gt 0) { exit 1 }

if (Test-SigningConfigured) {
    Write-Host "Desktop signing preflight: CSC_* configured." -ForegroundColor Green
} else {
    Write-Host "Desktop signing preflight: unsigned build path OK." -ForegroundColor Green
}
exit 0
