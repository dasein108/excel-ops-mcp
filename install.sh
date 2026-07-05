#!/bin/sh
# excel-ops-mcp installer bootstrap (POSIX).
# Usage: curl -LsSf https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.sh | sh
set -eu

if ! command -v uv >/dev/null 2>&1; then
  echo "excel-ops-mcp: installing uv (provides Python + uvx)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installs to ~/.local/bin by default.
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v uvx >/dev/null 2>&1; then
  echo "excel-ops-mcp: uvx not found on PATH after installing uv." >&2
  echo "Add uv's bin dir to PATH (usually ~/.local/bin) and re-run." >&2
  exit 1
fi

# uvx caches resolved versions, so a plain re-run keeps using the old release.
# Clear the cached excel-ops-mcp so this run — and the server that agents launch
# via `uvx excel-ops-mcp` — picks up the latest published version.
echo "excel-ops-mcp: updating to the latest published version..."
uv cache clean excel-ops-mcp >/dev/null 2>&1 || true

echo "excel-ops-mcp: launching installer..."
# Interactive picker needs a terminal on stdin. When stdin is already a terminal
# (direct run), use it as-is — reopening /dev/tty there breaks the picker on
# macOS. When stdin is a pipe (`curl ... | sh`), reattach /dev/tty, but only if
# it is actually openable — in CI/sandbox/cron it can exist yet fail to open, so
# fall back to a non-interactive run there.
if [ -t 0 ]; then
  exec uvx --refresh-package excel-ops-mcp --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@"
elif ( : < /dev/tty ) 2>/dev/null; then
  exec uvx --refresh-package excel-ops-mcp --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@" </dev/tty
else
  exec uvx --refresh-package excel-ops-mcp --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@"
fi
