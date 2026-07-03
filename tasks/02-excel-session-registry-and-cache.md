---
title: "Excel Session Registry and Cache"
status: done
phase: P0
---

# Task 02 — Excel Session Registry and Cache

Implement workbook-level sessions so repeated reads and queries hit cached workbook state instead of reparsing the same file.

## Scope

- Local `.xlsx` files only.
- Cache key based on absolute path, file size, and mtime.
- Session IDs stable during server lifetime.
- Persistent SQLite metadata cache.
- In-memory LRU for parsed workbooks and DuckDB connections.

## Deliverables

- `spreadsheet_open(path)` implementation.
- Session registry with:
  - `session_id`
  - absolute path
  - file metadata
  - opened timestamp
  - last access timestamp
  - cached workbook handle
  - DuckDB connection placeholder
  - staged operations placeholder
- SQLite table for session metadata and observed workbook fingerprints.
- Cache invalidation when file mtime/size changes.
- Configurable TTL and max open workbooks.

## Acceptance Criteria

- Opening the same unchanged workbook twice reuses the existing session or returns a cache hit indicator.
- Changing the file invalidates the session.
- Session lookup fails clearly for unknown or stale session IDs.
- Unit tests cover cache hit, cache miss, and invalidation.

## Design Notes

This must be workbook-level caching, not `(tool_name, args)` caching. The target antipattern is many different range reads from the same workbook; per-call cache would miss all of those.

