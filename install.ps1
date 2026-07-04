# excel-ops-mcp installer bootstrap (Windows PowerShell).
# Usage: powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.ps1 | iex"
$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "excel-ops-mcp: installing uv (provides Python + uvx)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) {
    Write-Error "uvx not found after installing uv. Add uv's bin dir to PATH and re-run."
    exit 1
}

Write-Host "excel-ops-mcp: launching installer..."
uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install $args
