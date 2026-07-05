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
# Only reattach the terminal when stdin is NOT already interactive — i.e. the
# `curl ... | sh` case, where stdin is the pipe. When run directly, stdin is
# already the terminal; reopening /dev/tty there breaks the picker on macOS.
if [ -t 0 ] || [ ! -e /dev/tty ]; then
  exec uvx --refresh-package excel-ops-mcp --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@"
else
  exec uvx --refresh-package excel-ops-mcp --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@" </dev/tty
fi
