# Excel MCP

Excel MCP is a Python MCP server and companion CLI for safe, token-efficient work with local Excel `.xlsx` workbooks.

It is designed for financial and operations workflows such as bookkeeping, accounting, marketing operations, SEO exports, research tables, reconciliations, and financial report review.

Core behavior:

- Describe workbook structure before reading bulk data.
- Query detected worksheet regions with DuckDB SQL.
- Inspect exact ranges only when needed.
- Stage writes as dry-runs.
- Diff before commit.
- Save edits to a new workbook by default.
- Keep an audit trail of reads, queries, staged writes, diffs, commits, and failures.

Google Sheets and Apple Numbers are not supported in this phase.

## Install

### Recommended: `uvx`

If `uv` is installed, run the MCP server without creating a virtual environment:

```bash
uvx excel-ops-mcp
```

Run the CLI without a persistent install:

```bash
uvx --from excel-ops-mcp excel-ops sheets workbook.xlsx
```

### One-command install (all agents)

Bootstraps `uv` if needed, then opens a picker to install `excel-ops-mcp` into
Claude Desktop, Claude Code, Codex, Gemini CLI, Cursor, and/or Windsurf:

```bash
curl -LsSf https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.ps1 | iex"
```

The picker pre-checks agents that already have `excel-ops-mcp` (none on a fresh
machine). Checking an agent installs it; **unchecking an installed agent
uninstalls it**.

Non-interactive: `... | sh -s -- --agents cursor,claude-code` to install, or
`--uninstall cursor,claude-code` to remove. Preview with `--dry-run`; see status
with `--list`.

### Install `uv`

macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Homebrew:

```bash
brew install uv
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, restart your shell if `uvx` is not found.

### Persistent CLI Install

Use `pipx` if you want `excel-ops-mcp` and `excel-ops` installed persistently:

```bash
pipx install excel-ops-mcp
excel-ops sheets workbook.xlsx
```

### Developer Install

```bash
git clone <repo-url>
cd excel_mcp
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,install]"
pytest -v
```

## MCP Configuration

The fastest way to configure any supported host (Claude Desktop, Claude Code,
Codex, Gemini CLI, Cursor, Windsurf) is the [one-command installer](#one-command-install-all-agents),
which writes the correct config for each agent automatically.

To configure a host manually, for MCP hosts that support command-based servers:

```json
{
  "mcpServers": {
    "excel-mcp": {
      "command": "uvx",
      "args": ["excel-ops-mcp"]
    }
  }
}
```

For local development:

```json
{
  "mcpServers": {
    "excel-mcp": {
      "command": "/absolute/path/to/excel_mcp/.venv/bin/excel-ops-mcp"
    }
  }
}
```

## MCP Tools

### `spreadsheet_open`

Open a local `.xlsx` workbook and return a session ID.

Input:

```json
{
  "path": "/path/to/workbook.xlsx"
}
```

Output includes:

- `session_id`
- resolved path
- file size
- mtime
- cache telemetry

### `spreadsheet_describe`

Describe workbook sheets, detected regions, SQL table names, columns, formulas, merged ranges, and source references.

Input:

```json
{
  "session_id": "ses_...",
  "detail": "compact"
}
```

Use `detail: "standard"` only when sample rows are needed. Compact mode avoids long cell text by default.

### `spreadsheet_query`

Run read-only DuckDB SQL over detected workbook regions.

Input:

```json
{
  "session_id": "ses_...",
  "sql": "select line_item, jan from \"revenue_model_table_1\" limit 5",
  "limit": 1000
}
```

Mutation statements are rejected. Writes must go through structured write operations.

Percent-like columns may expose derived numeric columns:

- `<column>__kind`
- `<column>__num`
- `<column>__min`
- `<column>__max`

Use `__max` for mixed APY/range values such as `0.34`, `10-30%`, and `от 11% до 80%+`.

### `spreadsheet_read_range`

Read a bounded cell range for exact inspection.

Input:

```json
{
  "session_id": "ses_...",
  "sheet": "Sheet1",
  "range": "A1:F20",
  "include": ["values", "formulas"]
}
```

Supported `include` values:

- `values` — computed value. Formula cells return the number Excel cached in the file, not the formula text.
- `formulas` — the formula string (e.g. `=B11+B16+B20`).
- `number_formats`
- `comments`
- `hyperlinks`
- `styles`
- `merged`

`spreadsheet_query` likewise materializes computed values, so SQL can aggregate
formula columns. When a formula has no cached value (files never opened in a
spreadsheet app), the cell returns null with a `computed_value_unavailable`
warning; install the recompute extra to evaluate it:

```bash
pip install 'excel-ops-mcp[recompute]'
```

### `spreadsheet_trace`

Trace a cell's formula lineage — its precedents, cross-sheet aware, with computed
values, recursing up to `depth` (0–5).

Input:

```json
{ "session_id": "ses_...", "sheet": "Dashboard", "cell": "B5", "depth": 2 }
```

Returns `target` with `formula`, `value`, and a nested `precedents` tree. Use it to
answer "where does this number come from?" and "how is X computed?" instead of
hand-parsing formulas.

### `spreadsheet_write`

Stage structured write operations. This is a dry-run preview and does not mutate the source file.

Input:

```json
{
  "session_id": "ses_...",
  "dry_run": true,
  "operations": [
    {
      "type": "set_values",
      "sheet": "Ops",
      "start": "E2",
      "values": [["reviewed"]]
    }
  ]
}
```

Supported operations:

- `set_values`
- `set_formula`
- `clear_range`
- `append_rows`
- `insert_rows`
- `delete_rows`
- `copy_range`

### `spreadsheet_diff`

Return the staged diff before commit.

Input:

```json
{
  "session_id": "ses_...",
  "staged_id": "stg_..."
}
```

### `spreadsheet_commit`

Commit staged changes to a workbook file. Saves to a new output path by default.

Input:

```json
{
  "session_id": "ses_...",
  "staged_id": "stg_...",
  "output_path": "/path/to/workbook.updated.xlsx",
  "overwrite": false
}
```

Source overwrite is rejected unless `overwrite` is explicitly true.

## CLI

The `excel-ops` CLI exposes the same engine without starting an MCP server.

### Command Reference

Every base command, and the MCP tool it mirrors:

| CLI command | MCP tool | Purpose |
| --- | --- | --- |
| `excel-ops open <file.xlsx>` | `spreadsheet_open` | Open a workbook and return a session id |
| `excel-ops sheets <file.xlsx>` | `spreadsheet_describe` (compact) | List worksheet names |
| `excel-ops tables <file.xlsx>` | `spreadsheet_describe` | List detected SQL table names and columns |
| `excel-ops describe <file.xlsx>` | `spreadsheet_describe` | Full structure (add `--detail standard` for sample rows) |
| `excel-ops query <file.xlsx> --sql "..."` | `spreadsheet_query` | Run read-only DuckDB SQL |
| `excel-ops read-range <file.xlsx> --sheet S --range A1:B10` | `spreadsheet_read_range` | Inspect exact cells, formulas, or formatting |
| `excel-ops trace <file.xlsx> --sheet S --cell B5 --depth 2` | `spreadsheet_trace` | Trace a cell's formula lineage (precedents) |
| `excel-ops write --session ses --ops ops.json` | `spreadsheet_write` | Stage write operations (dry-run) |
| `excel-ops diff --session ses --staged stg` | `spreadsheet_diff` | Show the staged diff before commit |
| `excel-ops commit --session ses --staged stg --output new.xlsx` | `spreadsheet_commit` | Save staged changes to a new workbook |
| `excel-ops audit --session ses` | — | Show the read/query/stage/commit trail |

Shared flags: `--pretty` (readable JSON), `--allowed-root <dir>` (permit paths outside the current directory), `--cache-dir <dir>` (persist session and staged ids across chained commands).

### Discover Sheets

```bash
excel-ops sheets examples/Financial_Report.xlsx --pretty
```

### Discover Tables

```bash
excel-ops tables examples/saas.xlsx --pretty
```

Filter to a sheet:

```bash
excel-ops tables examples/saas.xlsx --sheet "Revenue Model" --pretty
```

### Query

```bash
excel-ops query examples/saas.xlsx \
  --sql 'select line_item, jan from "revenue_model_table_1" limit 5' \
  --pretty
```

### Read A Range

```bash
excel-ops read-range examples/saas.xlsx \
  --sheet "Revenue Model" \
  --range A1:D5 \
  --include values \
  --pretty
```

### Safe Write Workflow

Open a workbook and keep the same cache directory across commands:

```bash
excel-ops open workbook.xlsx --cache-dir /tmp/excel-ops-cache --pretty
```

Create operations:

```json
[
  {
    "type": "set_values",
    "sheet": "Ops",
    "start": "E2",
    "values": [["reviewed"]]
  }
]
```

Stage the write:

```bash
excel-ops write --session ses_... --ops ops.json --cache-dir /tmp/excel-ops-cache --pretty
```

Review the diff:

```bash
excel-ops diff --session ses_... --staged stg_... --cache-dir /tmp/excel-ops-cache --pretty
```

Commit to a new workbook:

```bash
excel-ops commit \
  --session ses_... \
  --staged stg_... \
  --output workbook.updated.xlsx \
  --cache-dir /tmp/excel-ops-cache \
  --pretty
```

### Audit Trail

```bash
excel-ops audit --session ses_... --cache-dir /tmp/excel-ops-cache --pretty
```

## Use as an Agent Skill

The Excel workflow ships as a single, harness-agnostic skill so the same guidance works from Claude Code, Codex, or any MCP host. There is one source of truth and thin per-harness pointers.

Canonical skill (edit here):

```text
agents/skills/excel-ops/SKILL.md
agents/skills/excel-ops/references/cli-workflows.md
```

Per-harness pointers (load the skill in each tool, frontmatter only):

- Claude Code / Claude plugins: `.claude/skills/excel-ops/SKILL.md`
- Codex: `.codex/skills/excel-ops/SKILL.md` (plus Codex host config `agents/openai.yaml`)

All three delivery channels drive the same engine:

- **MCP host** — the `spreadsheet_*` tools above.
- **CLI** — the `excel-ops` commands above.
- **Agent skill** — tells the agent to prefer the `excel-ops` CLI over ad hoc scripts and to follow the stage → diff → commit safety contract.

The skill teaches this order: `sheets` → `tables` → `query` → `read-range` (exact inspection only) → `write` → `diff` → `commit` → `audit`.

The CLI is the deterministic interface. The skill is only guidance; it never implements spreadsheet logic itself.

## Safety Model

- Only local `.xlsx` files are supported.
- Paths are restricted to configured allowed roots.
- SQL is read-only.
- Writes are structured JSON operations.
- Writes are staged before commit.
- Commit saves to a new file unless overwrite is explicit.
- Audit events are stored in the configured cache directory.

## Background & Research

This project's design — DuckDB SQL over detected regions, workbook sessions, and a stage → diff → commit write contract — draws on a survey of the Excel/spreadsheet MCP landscape and a DuckDB-aware architecture comparison. See [docs/RESEARCH_AND_COMPETITORS.md](docs/RESEARCH_AND_COMPETITORS.md).

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for local development, tests, package builds, and PyPI release automation.

