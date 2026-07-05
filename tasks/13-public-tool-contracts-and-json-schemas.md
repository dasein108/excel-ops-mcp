---
title: "Public Tool Contracts and JSON Schemas"
status: done
phase: P0
---

# Task 13 — Public Tool Contracts and JSON Schemas

Define the public MCP tool contracts before implementing the internals.

## Scope

- Stable JSON request/response schemas.
- Error envelope.
- Common source citation shape.
- Common telemetry shape.
- Common truncation shape.

## Tools

The initial tool surface is:

- `spreadsheet_open`
- `spreadsheet_describe`
- `spreadsheet_query`
- `spreadsheet_read_range`
- `spreadsheet_write`
- `spreadsheet_commit`
- `spreadsheet_diff`

## Common Response Fields

Every successful response should support:

```json
{
  "ok": true,
  "session_id": "ses_...",
  "source_refs": ["file.xlsx#Sheet1!A1:F20"],
  "warnings": [],
  "telemetry": {
    "cache": "hit",
    "elapsed_ms": 12
  }
}
```

Every failed response should use:

```json
{
  "ok": false,
  "error": {
    "code": "invalid_range",
    "message": "Range must be bounded",
    "details": {}
  }
}
```

## Request Sketches

`spreadsheet_open`:

```json
{
  "path": "/absolute/path/workbook.xlsx"
}
```

`spreadsheet_describe`:

```json
{
  "session_id": "ses_...",
  "detail": "compact"
}
```

`spreadsheet_query`:

```json
{
  "session_id": "ses_...",
  "sql": "select category, sum(amount) from Transactions group by 1",
  "limit": 1000
}
```

`spreadsheet_read_range`:

```json
{
  "session_id": "ses_...",
  "sheet": "Transactions",
  "range": "A1:F50",
  "include": ["values", "formulas"]
}
```

`spreadsheet_write`:

```json
{
  "session_id": "ses_...",
  "dry_run": true,
  "operations": []
}
```

`spreadsheet_commit`:

```json
{
  "session_id": "ses_...",
  "staged_id": "stg_...",
  "output_path": "/absolute/path/workbook.updated.xlsx",
  "overwrite": false
}
```

`spreadsheet_diff`:

```json
{
  "session_id": "ses_...",
  "staged_id": "stg_..."
}
```

## Acceptance Criteria

- Pydantic models exist for every request and response.
- JSON schema can be exported for each tool.
- Error codes are documented.
- The schemas are used by placeholder tools from Task 01.
- Tests validate example payloads.

## Notes

Locking schemas first prevents the implementation from leaking internal library details into the MCP interface.

## v2 fat tools

The MCP surface consolidates the original ten flat tools into four fat, mode-based
tools. See `docs/superpowers/specs/2026-07-05-mcp-tool-consolidation-design.md` for
the rationale (fewer schema-load waves, fewer round-trips, server-side aggregation).

### Hybrid source rule

Every v2 tool takes its source as one of, in precedence order:

1. `session_id` — reuse an already-open workbook (cache hit).
2. `content_base64` + `filename` — upload bytes (for hosts that don't share the server filesystem).
3. `path` — a host path under an allowed root (auto-opens; a repeat path is a cache hit).

No separate `spreadsheet_open` call is required. Every response echoes `session_id`
(including error responses once a session has been resolved) so follow-up calls skip
re-parsing. Missing all three sources returns `error_response("missing_source", ...)`.

### `spreadsheet_inspect`

Read-side tool. Params: `mode` (`describe` | `read` | `trace` | `summary`), the hybrid
source keys, plus mode-specific: `sheet`, `range`, `cell`, `depth`, `include`, `detail`,
`growth`. Unknown mode → `error_response("invalid_mode", ...)`.

- `mode=describe` → `SpreadsheetDescribeResponse`, now including `best_source`: a
  list (top 3) of `{sheet, reason, score}` ranking sheets so the cleanest aggregated
  sheet surfaces first. Advisory only — it never changes which sheet a later call uses.
  Ranking weights `region_kind` (summary > table > ledger > parameters > metadata >
  unknown) plus detection confidence; matrix-layout summary regions that persist as
  `region_kind="table"` are recovered from their row-label text ("total"/"summary")
  for ranking without mutating `region_kind`.
- `mode=summary` → `SpreadsheetSummaryResponse` with server-computed fields: `count`,
  `skipped`, `total`, `mean`, `min`, `max`, and `yoy_growth_pct` (per-step percent
  change, populated when `growth=true`). Non-numeric cells are skipped and counted;
  booleans are not treated as numbers. The model reads results instead of summing cells.
- `mode=read` → `SpreadsheetReadRangeResponse`; capped at `config.read_row_limit`
  (default 200) with `telemetry.truncated` / `telemetry.rows_returned` set when clipped.
- `mode=trace` → `SpreadsheetTraceResponse` (formula precedents to `depth`).

### `spreadsheet_query`

Read-only DuckDB SQL. Params: hybrid source keys, `sql`, `limit`. Resolves the source
first when no `session_id` is given, then runs SQL. Response `SpreadsheetQueryResponse`.

### `spreadsheet_edit`

Write tool: stage and optionally commit in one call. Params: hybrid source keys,
`operations` (same op shapes as the v1 `spreadsheet_write`: set_values, set_formula,
clear_range, append_rows, insert_rows, delete_rows, copy_range), `dry_run` (default
false), `commit` (default true), `output_path`, `overwrite`. Behavior: always stages
internally; returns the stage response (no file written) when staging fails, has
`rejected_operations`, `dry_run=true`, or `commit=false`; otherwise commits and returns
`SpreadsheetCommitResponse` (`output_path`, `changes`). Rejected operations never write.

### `spreadsheet_list`

Lists `.xlsx` workbooks under the allowed roots. Params: `glob`, `limit`. Delegates to
the v1 `workbook_list` engine; response `WorkbookListResponse`.

### Deprecation window

The v1 tools — `spreadsheet_open`, `workbook_list`, `spreadsheet_describe`,
`spreadsheet_read_range`, `spreadsheet_trace`, `spreadsheet_write`, `spreadsheet_commit`,
`spreadsheet_diff` — remain fully functional for one minor release as deprecated shims;
their FastMCP docstrings carry a `[DEPRECATED — use spreadsheet_inspect/edit/list]`
prefix. Removal is a subsequent version bump.

