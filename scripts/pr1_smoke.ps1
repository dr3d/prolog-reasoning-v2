[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipLiveMcp,
    [string]$BaseUrl = "http://127.0.0.1:1234",
    [string]$Model = "qwen/qwen3.5-9b",
    [string]$Integration = "mcp/prolog-reasoning",
    [string]$OutDir = ".tmp_pr1_smoke_surface"
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

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Push-Location $repoRoot
try {
    Write-Host "=== PR1 Smoke: deterministic checks ==="
    & $Python scripts/check_docs_consistency.py
    & $Python -m pytest tests/test_write_path_validator.py -q
    & $Python -m pytest tests/test_mcp_server.py -q
    & $Python -m pytest tests -q

    if ($SkipLiveMcp) {
        Write-Host "=== PR1 Smoke: live MCP check skipped (--SkipLiveMcp) ==="
        Write-Host "PR1 SMOKE: PASS (deterministic checks only)"
        exit 0
    }

    Write-Host "=== PR1 Smoke: live MCP surface check ==="
    Remove-SafelyWithinRepo -TargetPath $OutDir -RepoRoot $repoRoot
    & $Python scripts/capture_mcp_surface_playbook_session.py `
        --base-url $BaseUrl `
        --model $Model `
        --integration $Integration `
        --validate `
        --out-dir $OutDir

    Write-Host "PR1 SMOKE: PASS"
    Write-Host "Live capture artifacts: $OutDir"
    exit 0
}
finally {
    Pop-Location
}
