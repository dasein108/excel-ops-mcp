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

echo "excel-ops-mcp: launching installer..."
# Under `curl ... | sh`, stdin is the pipe, so reattach the terminal to let the
# interactive picker read keystrokes. Falls back to non-interactive (applies to
# detected agents) when no terminal is available (e.g. CI).
if [ -e /dev/tty ]; then
  exec uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@" </dev/tty
else
  exec uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@"
fi
