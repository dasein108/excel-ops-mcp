---
title: "Structured Batch Write Operations"
status: done
phase: P1
---

# Task 07 — Structured Batch Write Operations

Implement structured Excel write operations. Writes should be explicit, batchable, and auditable.

## Scope

- Local `.xlsx` writes through `openpyxl`.
- Staged operations in the session.
- Dry-run by default.
- No SQL writes.

## Operations

Support:

- `set_values`
- `set_formula`
- `clear_range`
- `append_rows`
- `insert_rows`
- `delete_rows`
- `copy_range`

Later:

- `set_number_format`
- `copy_style_from_row`
- `resize_table`

## Deliverables

- `spreadsheet_write(session_id, operations, dry_run=true)`.
- Pydantic models for each operation.
- Operation validation before mutation.
- Warning detection for:
  - formulas in touched area
  - merged cells
  - protected sheets
  - hidden rows/columns
  - Excel tables/ListObjects
  - named ranges crossing edit area

## Acceptance Criteria

- Multiple cell/range edits can be submitted in one call.
- Formula writes preserve formulas as formulas.
- Invalid cell/range references fail before any mutation.
- Dry-run response reports exact touched ranges.
- Tests cover batch writes to values and formulas.

## Product Notes

For accounting/bookkeeping, batch writes are needed for categorization, reconciliation flags, notes, adjusted values, and generated summary tabs.

