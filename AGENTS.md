# Repository Instructions

## Excel Operation Parity

When adding, modifying, or removing an Excel operation, keep all public surfaces in sync:

- MCP/tool layer in `excel_mcp/tools.py` and related core modules.
- CLI surface in `excel_mcp/cli.py` under the `excel-ops` command.
- Canonical agent skill in `agents/skills/excel-ops/SKILL.md` and `agents/skills/excel-ops/references/cli-workflows.md` when usage changes. The per-harness pointers `.codex/skills/excel-ops/SKILL.md` and `.claude/skills/excel-ops/SKILL.md` stay thin — update their frontmatter `description` only, never duplicate the guide body there.
- Tests for direct tools and CLI subprocess behavior.

## Cross-Agent Installer

The installer in `excel_mcp/installer/` writes MCP config for external agents
(Claude Desktop, Claude Code, Codex, Gemini CLI, Cursor, Windsurf). When an
agent changes its config path or format, update the matching adapter under
`excel_mcp/installer/adapters/` (or the descriptor in `registry.py`) and its
test in `tests/installer/`. Adapters must stay safe: never clobber other
servers, back up before writing, and remain idempotent.

Do not implement spreadsheet logic separately in the CLI. The CLI must remain a thin adapter over the same core used by the MCP tools.

For writes, preserve the safety contract across both MCP and CLI:

- Stage/dry-run first.
- Diff before commit.
- Commit to a new workbook by default.
- Reject source overwrite unless explicitly requested.

Google Sheets and Numbers are out of scope for this repository phase unless the roadmap changes explicitly.

