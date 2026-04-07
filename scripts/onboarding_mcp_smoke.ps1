[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$BaseUrl = "http://127.0.0.1:1234",
    [string]$Model = "qwen/qwen3.5-9b",
    [string]$Integration = "mcp/prolog-reasoning",
    [string]$OutRoot = ".tmp_onboarding_mcp_smoke",
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Stop"

function Remove-SafelyWithinRepo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        return
    }

    $resolvedTarget = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $TargetPath).Path)
    $resolvedRepo = [System.IO.Path]::GetFullPath($RepoRoot)
    if (-not $resolvedRepo.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $resolvedRepo += [System.IO.Path]::DirectorySeparatorChar
    }

    if (-not $resolvedTarget.StartsWith($resolvedRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside repo root: $resolvedTarget"
    }

    Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
}

function Invoke-CaptureStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string]$OutputDir,
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$BaseUrlValue,
        [Parameter(Mandatory = $true)]
        [string]$ModelValue,
        [Parameter(Mandatory = $true)]
        [string]$IntegrationValue
    )

    Write-Host ""
    Write-Host "=== Running: $Name ==="

    $priorErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $stepOutput = & $PythonExe $ScriptPath `
            --validate `
            --base-url $BaseUrlValue `
            --model $ModelValue `
            --integration $IntegrationValue `
            --out-dir $OutputDir 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $priorErrorAction
    }

    foreach ($line in $stepOutput) {
        Write-Host $line
    }
    if ($exitCode -ne 0) {
        return [PSCustomObject]@{
            Name   = $Name
            Passed = $false
        }
    }

    return [PSCustomObject]@{
        Name   = $Name
        Passed = $true
    }
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Push-Location $repoRoot
try {
    if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
        throw "Python executable not found: $Python"
    }

    if (-not $env:LMSTUDIO_API_KEY -and -not $env:OPENAI_API_KEY) {
        Write-Host "Note: no LMSTUDIO_API_KEY/OPENAI_API_KEY detected in current shell."
        Write-Host "If LM Studio API auth is enabled, captures will fail with HTTP 401."
    }

    Remove-SafelyWithinRepo -TargetPath $OutRoot -RepoRoot $repoRoot
    New-Item -ItemType Directory -Path $OutRoot -Force | Out-Null

    $hospitalOut = Join-Path $OutRoot "hospital"
    $fantasyOut = Join-Path $OutRoot "fantasy"
    $surfaceOut = Join-Path $OutRoot "surface"

    $results = @()
    $results += Invoke-CaptureStep `
        -Name "Hospital MCP Playbook Capture" `
        -ScriptPath "scripts/capture_hospital_playbook_session.py" `
        -OutputDir $hospitalOut `
        -PythonExe $Python `
        -BaseUrlValue $BaseUrl `
        -ModelValue $Model `
        -IntegrationValue $Integration

    $results += Invoke-CaptureStep `
        -Name "Fantasy Overlord Capture" `
        -ScriptPath "scripts/capture_fantasy_overlord_session.py" `
        -OutputDir $fantasyOut `
        -PythonExe $Python `
        -BaseUrlValue $BaseUrl `
        -ModelValue $Model `
        -IntegrationValue $Integration

    $results += Invoke-CaptureStep `
        -Name "MCP Surface Sanity Capture" `
        -ScriptPath "scripts/capture_mcp_surface_playbook_session.py" `
        -OutputDir $surfaceOut `
        -PythonExe $Python `
        -BaseUrlValue $BaseUrl `
        -ModelValue $Model `
        -IntegrationValue $Integration

    Write-Host ""
    Write-Host "=== Onboarding MCP Smoke Summary ==="
    foreach ($result in $results) {
        $status = if ($result.Passed) { "PASS" } else { "FAIL" }
        Write-Host ("{0} - {1}" -f $status, $result.Name)
    }

    $allPassed = ($results | Where-Object { -not $_.Passed }).Count -eq 0
    if ($allPassed) {
        Write-Host ""
        Write-Host "ONBOARDING MCP SMOKE: PASS"
        if (-not $KeepArtifacts) {
            Remove-SafelyWithinRepo -TargetPath $OutRoot -RepoRoot $repoRoot
        } else {
            Write-Host "Artifacts kept at: $OutRoot"
        }
        exit 0
    }

    Write-Host ""
    Write-Host "ONBOARDING MCP SMOKE: FAIL"
    Write-Host "Artifacts kept at: $OutRoot"
    exit 1
}
finally {
    Pop-Location
}
