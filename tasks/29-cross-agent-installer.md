---
title: "Cross-agent Installer"
status: draft
scope: distribution
source: "superpowers spec 2026-07-04 (approved)"
---

# Cross-agent Installer

Give users a single command that installs `excel-ops-mcp` and wires it into whichever
LLM agents/apps they choose. Bootstraps `uv`/`uvx` from scratch, then runs a TUI to
pick agents and writes each agent's MCP config safely.

Target agents (v1): Claude Desktop, Claude Code, Codex, Gemini CLI, Cursor,
Windsurf. Target OSes (v1): macOS, Linux, Windows. Ships as **v0.2.0**.

## Delivery / bootstrap

- `install.sh` (POSIX) and `install.ps1` (PowerShell) at repo root, served raw
  from GitHub.
- One-liner:
  `curl -LsSf https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.sh | sh`
  (Windows: `irm https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.ps1 | iex`)
- Bootstrap logic: if `uv` not on PATH, install it via the official astral
  installer; then run `uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install`
  (passes through any CLI args).
- No separate Python install: `uv` provides managed Python, and the MCP runs via
  `uvx` self-contained. The installer states this in its output.

## Packaging

- Installer ships **inside** the `excel-ops-mcp` package — no second package.
- New module `excel_mcp/installer/`.
- New console script: `excel-ops-mcp-install = "excel_mcp.installer.cli:main"`.
- `questionary` added under a new optional extra `install = ["questionary>=2.0"]`.
  Base package stays lean; bootstrap always pulls the extra via
  `excel-ops-mcp[install]`.

## Module layout

```
excel_mcp/installer/
  cli.py          # entrypoint: arg parsing, orchestration, summary output
  spec.py         # the server spec: {"command":"uvx","args":["excel-ops-mcp"]}
  tui.py          # questionary checkbox; thin — no business logic
  detect.py       # shared detection helpers (PATH lookup, file existence)
  adapters/
    base.py       # AgentAdapter interface
    claude_desktop.py
    claude_code.py
    codex.py
    gemini.py
    cursor.py
    windsurf.py
  merge.py        # safe JSON / TOML merge + backup helpers
```

## Adapter interface

```python
class AgentAdapter:
    key: str            # "claude-desktop", stable id for --agents flag
    label: str          # "Claude Desktop", shown in TUI
    def detect(self) -> bool: ...          # installed on this machine?
    def config_path(self) -> Path | None:  # OS-resolved target file
    def apply(self, spec: ServerSpec) -> ApplyResult: ...  # merge+backup+write
```

`ApplyResult` records: path written, backup path, created-vs-updated, any note
(e.g. "restart Claude Desktop").

### Per-agent mechanics

| Agent | Mechanism | Location (mac / win / linux) |
|---|---|---|
| Claude Desktop | merge JSON `mcpServers` | `~/Library/Application Support/Claude/claude_desktop_config.json` / `%APPDATA%\Claude\claude_desktop_config.json` / `~/.config/Claude/claude_desktop_config.json` |
| Claude Code | `claude mcp add excel-ops-mcp -- uvx excel-ops-mcp` if `claude` on PATH; else merge `~/.claude.json` | CLI-driven |
| Codex | merge TOML `[mcp_servers.excel-ops-mcp]` | `~/.codex/config.toml` |
| Gemini CLI | merge JSON `mcpServers` | `~/.gemini/settings.json` |
| Cursor | merge JSON `mcpServers` (global) | `~/.cursor/mcp.json` |
| Windsurf | merge JSON `mcpServers` | `~/.codeium/windsurf/mcp_config.json` |

Exact paths/keys are verified against current agent docs during implementation
(they drift); the table is the intended shape.

## Server spec written

JSON agents:
```json
{ "mcpServers": { "excel-ops-mcp": { "command": "uvx", "args": ["excel-ops-mcp"] } } }
```
Codex (TOML):
```toml
[mcp_servers.excel-ops-mcp]
command = "uvx"
args = ["excel-ops-mcp"]
```

## TUI behavior

- `questionary` checkbox list of all six agents.
- Detected agents pre-checked; missing ones labeled `(not found)` but still
  selectable (user may install the app later).
- Space toggles, enter confirms.
- Fallbacks: if stdout is not a TTY, or `--yes`/`--agents` given, skip the TUI.

## CLI flags

- `--agents claude-desktop,cursor` — non-interactive selection.
- `--yes` — no prompts, apply to detected (or `--agents`) set.
- `--dry-run` — show what would change, write nothing.
- `--list` — print detection results and exit.

## Safety (non-negotiable)

- **Never clobber**: read existing config, insert/update only the `excel-ops-mcp`
  entry, preserve all other servers and unrelated keys.
- **Backup**: copy each target to `<name>.bak` before writing.
- **Idempotent**: re-running updates the entry in place, no duplicates.
- Create parent dirs / fresh config only for agents actually selected.
- Malformed existing config → do not overwrite; report and skip that agent.
- Final summary: per-agent written path, backup path, created/updated, restart notes.

## Testing

- Per-adapter unit tests over tmp files: merge preserves existing servers + unrelated
  keys; creates valid config when absent; idempotent on re-run; correct command/args
  shape (JSON and TOML); malformed input not clobbered.
- Detection tests with faked PATH / file locations.
- CLI tests: `--dry-run` writes nothing; `--agents` selects correctly; `--list` output.
- TUI kept thin; business logic lives in adapters (tested). No TUI automation in v1.

## Out of scope (v1, YAGNI)

- Uninstall command.
- Per-project (vs global) config choice.
- Agents beyond the six listed.
- Full-screen TUI.
