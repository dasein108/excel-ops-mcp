---
title: "DuckDB Materialization and SQL Query"
status: done
phase: P0
---

# Task 05 — DuckDB Materialization and SQL Query

Materialize detected Excel regions into DuckDB and expose read-only SQL through `spreadsheet_query`.

## Scope

- Read-only SQL.
- Detected regions become DuckDB tables/views.
- Type inference for common spreadsheet values.
- Safe table and column naming.
- Default row and character caps.

## Deliverables

- DuckDB connection per active session.
- Region-to-table materialization.
- Column deduplication and sanitization.
- Type inference:
  - boolean
  - integer
  - decimal
  - date
  - timestamp
  - text
- `spreadsheet_query(session_id, sql, limit?)`.
- SQL validation that rejects mutation statements.
- Query result includes:
  - columns
  - rows
  - row count
  - truncated flag
  - source table references when possible
  - execution time

## Acceptance Criteria

- Supports `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `JOIN`, CTEs, and window functions.
- Rejects `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `COPY`, `ATTACH`, and extension-loading statements.
- Defaults to 1,000 returned rows and 50,000 response chars.
- Can query across multiple detected regions in the same workbook.
- Tests cover accounting-style queries:
  - totals by month
  - duplicates
  - unmatched payments
  - top vendors
  - variance by category

## Notes

SQL is the primary read interface because it gives maximum analytical power with minimal token load. SQL must not be used for writes.

