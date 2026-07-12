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

# uvx caches resolved versions; clear the cached excel-ops-mcp so this run — and
# the server that agents launch via `uvx excel-ops-mcp` — uses the latest release.
Write-Host "excel-ops-mcp: checking for the latest published version..."
uv cache clean excel-ops-mcp 2>$null

# Resolve + report the version that will be installed (also warms the cache).
$version = (uvx --refresh-package excel-ops-mcp --from "excel-ops-mcp[install]" `
  python -c "import importlib.metadata as m; print(m.version('excel-ops-mcp'))" 2>$null)
if ($version) { Write-Host "excel-ops-mcp: installing version $version" }
else { Write-Host "excel-ops-mcp: installing the latest version" }

Write-Host "excel-ops-mcp: launching installer..."
uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install $args
