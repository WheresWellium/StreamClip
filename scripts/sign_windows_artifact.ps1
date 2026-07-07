# Sign a Windows PE binary with Authenticode (§4.10).
# Requires CSC_LINK + CSC_KEY_PASSWORD (or -CertificatePath / -CertificatePassword).
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [string]$CertificatePath = $env:CSC_LINK,
    [string]$CertificatePassword = $env:CSC_KEY_PASSWORD,
    [string]$SignTool = $env:SIGNTOOL,
    [string]$TimestampUrl = $(if ($env:SIGN_TIMESTAMP_URL) { $env:SIGN_TIMESTAMP_URL } else { "http://timestamp.digicert.com" })
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Path)) {
    Write-Error "File not found: $Path"
}

if (-not $CertificatePath) {
    Write-Error "Set CSC_LINK or pass -CertificatePath"
}
if (-not $CertificatePassword) {
    Write-Error "Set CSC_KEY_PASSWORD or pass -CertificatePassword"
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
    Write-Error "signtool.exe not found. Install Windows SDK or set SIGNTOOL."
}

Write-Host "Signing $Path ..." -ForegroundColor Cyan
& $SignTool sign /fd SHA256 /tr $TimestampUrl /td SHA256 /f $CertificatePath /p $CertificatePassword $Path
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Signature applied." -ForegroundColor Green
