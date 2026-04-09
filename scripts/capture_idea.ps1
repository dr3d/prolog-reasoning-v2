param(
    [Parameter(Mandatory = $true)]
    [string]$Idea,
    [string]$Area = "general",
    [string]$Why = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$inboxPath = Join-Path $repoRoot "docs\research\idea-inbox.md"

if (!(Test-Path -LiteralPath $inboxPath)) {
    throw "Idea inbox file not found: $inboxPath"
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm 'ET'"
$line = "- [ ] $timestamp | area:$Area | idea: $Idea"
if ($Why.Trim().Length -gt 0) {
    $line += " | why: $Why"
}

Add-Content -LiteralPath $inboxPath -Value $line -Encoding UTF8
Write-Output "Captured idea in docs/research/idea-inbox.md"

