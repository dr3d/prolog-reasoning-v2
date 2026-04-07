[CmdletBinding()]
param(
    [string]$OutputDir = "sessions/backups",
    [switch]$SkipTracker
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$sessionsDir = Join-Path $repoRoot "sessions"
$trackerPath = Join-Path $repoRoot "sessions.md"

if (-not (Test-Path -LiteralPath $sessionsDir)) {
    throw "Sessions directory not found: $sessionsDir"
}

$resolvedOutputDir = if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    [System.IO.Path]::GetFullPath($OutputDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
}

New-Item -ItemType Directory -Path $resolvedOutputDir -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tempRoot = Join-Path $repoRoot ".tmp_sessions_backup_$stamp"
$zipPath = Join-Path $resolvedOutputDir "sessions-backup-$stamp.zip"

New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    Copy-Item -LiteralPath $sessionsDir -Destination (Join-Path $tempRoot "sessions") -Recurse -Force
    if (-not $SkipTracker -and (Test-Path -LiteralPath $trackerPath)) {
        Copy-Item -LiteralPath $trackerPath -Destination (Join-Path $tempRoot "sessions.md") -Force
    }

    Compress-Archive -Path (Join-Path $tempRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

Write-Output "Created backup: $zipPath"
