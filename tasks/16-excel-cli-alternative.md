---
title: "Excel CLI Alternative"
status: done
phase: P1
---

# Task 16 — Excel CLI Alternative

Create a deterministic CLI that exposes the same core Excel operations as the MCP tools, so Codex can work with Excel files in this project without starting an MCP server.

## Scope

- CLI over the existing Python core.
- Excel-only.
- Same safety behavior as MCP tools.
- JSON input/output by default.
- Human-readable output optional later.

## Command Name

Use `excel-ops` as the console script.

The user-facing skill may be called `excel_ops`, but Python package commands and Codex skill folders should use hyphen-case.

## Commands

Implement:

```text
excel-ops open PATH
excel-ops sheets PATH_OR_SESSION
excel-ops tables PATH_OR_SESSION
excel-ops describe --session SESSION_ID
excel-ops query --session SESSION_ID --sql SQL
excel-ops read-range --session SESSION_ID --sheet SHEET --range RANGE
excel-ops write --session SESSION_ID --ops OPS_JSON_OR_PATH
excel-ops diff --session SESSION_ID --staged STAGED_ID
excel-ops commit --session SESSION_ID --staged STAGED_ID --output OUTPUT_PATH
```

Also support a stateless convenience mode:

```text
excel-ops describe PATH
excel-ops query PATH --sql SQL
excel-ops read-range PATH --sheet SHEET --range RANGE
```

In stateless mode, the CLI should open the workbook internally and return the requested result in one invocation.

## Deliverables

- `excel_mcp/cli.py`.
- `pyproject.toml` console script entry for `excel-ops`.
- Common JSON printing helper.
- Exit codes:
  - `0` success
  - `1` tool-level failure with JSON error
  - `2` invalid CLI usage
- `--allowed-root` option, repeatable.
- `--cache-dir` option.
- `--pretty` option for indented JSON.
- `--output-profile compact|verbose` reserved flag, even if initially ignored.

## Acceptance Criteria

- CLI calls the same `ExcelMcpTools` methods as MCP tools.
- CLI never bypasses path policy or SQL policy.
- `excel-ops query PATH --sql ...` works against `examples/MEXC.xlsx`.
- `excel-ops write ...` stages changes but does not mutate source files.
- `excel-ops commit ... --output out.xlsx` saves to a new workbook.
- Tests cover success and failure exit codes.

## Notes

Do not duplicate spreadsheet logic in the CLI. The CLI is an adapter over the core tool layer.
