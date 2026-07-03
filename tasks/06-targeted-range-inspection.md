---
title: "Targeted Range Inspection"
status: done
phase: P1
---

# Task 06 — Targeted Range Inspection

Implement `spreadsheet_read_range` for exact inspection when SQL output is not enough.

## Scope

- Bounded range reads.
- Values, formulas, comments, formatting summary, and merged-cell information.
- Compact output profiles.

## Deliverables

`spreadsheet_read_range(session_id, sheet, range, include)` where `include` can request:

- values
- formulas
- number formats
- comments
- hyperlinks
- styles summary
- merged range membership

## Acceptance Criteria

- Requires an explicit bounded range.
- Refuses whole-sheet reads unless the used range is small and under cap.
- Returns `source_range`.
- Supports compact values-only mode.
- Tests cover formulas, comments, hyperlinks, and merged cells.

## Notes

This tool is for surgical inspection, not data analysis. The server should nudge users toward `spreadsheet_query` for tabular analysis.

