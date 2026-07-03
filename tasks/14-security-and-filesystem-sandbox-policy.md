---
title: "Security and Filesystem Sandbox Policy"
status: done
phase: P0
---

# Task 14 — Security and Filesystem Sandbox Policy

Define and implement local file safety rules for the Excel MCP.

## Scope

- Local Excel files only.
- Path validation.
- Read/write permissions.
- SQL sandboxing.
- Safe output path handling.

## Rules

- Only allow files under configured allowed roots.
- Refuse path traversal.
- Refuse URLs.
- Refuse symlink escapes unless explicitly configured.
- Support `.xlsx` first.
- `.xlsm` may be opened later, but macros are never executed.
- Do not support legacy `.xls` in P0.
- Do not overwrite source files by default.
- Output paths must also be under allowed roots.

## SQL Safety

`spreadsheet_query` must reject:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `DROP`
- `ALTER`
- `COPY`
- `ATTACH`
- `DETACH`
- `INSTALL`
- `LOAD`
- `CALL`
- `PRAGMA` unless explicitly whitelisted

## Deliverables

- `PathPolicy` module.
- `SqlPolicy` module.
- Config options for allowed roots and overwrite behavior.
- Structured errors for security failures.
- Tests for path traversal, symlinks, extension filtering, and SQL mutation blocking.

## Acceptance Criteria

- Unsafe paths never reach `openpyxl`.
- Unsafe SQL never reaches DuckDB execution.
- Commit refuses overwrite unless `overwrite=true`.
- Tests cover common bypass attempts.

## Product Notes

This MCP is likely to touch financial files. Safety defaults must be conservative even if it makes demos slightly less magical.

