---
title: "Dry-Run, Staging, Commit, and Diff"
status: done
phase: P1
---

# Task 08 — Dry-Run, Staging, Commit, and Diff

Make every write previewable and auditable before saving workbook changes.

## Scope

- Dry-run first.
- Staged write operations.
- Explicit commit.
- Save to new file by default.
- Diff summary after commit.

## Deliverables

- Dry-run result with:
  - operations accepted/rejected
  - cells/ranges touched
  - before/after preview for small changes
  - warnings
- Staging model:
  - staged operation ID
  - operation list
  - created timestamp
  - validation warnings
- `spreadsheet_commit(session_id, staged_id, output_path?)`.
- `spreadsheet_diff(session_id, staged_id?)`.

## Acceptance Criteria

- `spreadsheet_write` defaults to `dry_run=true`.
- No workbook file is changed during dry-run.
- Commit saves to a new file by default.
- Overwrite requires explicit option.
- Diff reports direct edits separately from unverified formula recalculation effects.
- Tests confirm original file bytes are unchanged after dry-run.

## Notes

This is mandatory for financial operations users. The model must show what it will change before changing it.

