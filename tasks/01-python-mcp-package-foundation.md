---
title: "Python MCP Package Foundation"
status: done
phase: P0
---

# Task 01 — Python MCP Package Foundation

Create the standalone Python MCP package skeleton for the Excel-only server.

## Scope

- Python package managed with `uv`.
- MCP server entrypoint.
- Basic configuration.
- Structured error envelope.
- Local filesystem path validation.
- No Excel parsing yet.

## Deliverables

- `pyproject.toml` with package metadata and console script.
- Source package, for example `excel_mcp/`.
- MCP server module with placeholder tools:
  - `spreadsheet_open`
  - `spreadsheet_describe`
  - `spreadsheet_query`
  - `spreadsheet_read_range`
  - `spreadsheet_write`
  - `spreadsheet_commit`
  - `spreadsheet_diff`
- Config module for:
  - allowed roots
  - max rows
  - max response chars
  - cache directory
  - default dry-run behavior
- Common response/error models.

## Acceptance Criteria

- Server starts over stdio.
- Tool schemas are visible to an MCP client.
- Invalid paths return structured errors, not tracebacks.
- Tools return `not_implemented` responses with stable JSON shapes.
- Unit tests cover config loading and path validation.

## Notes

Use a small tool surface. The goal is not many tools; it is high-quality, auditable Excel work.

