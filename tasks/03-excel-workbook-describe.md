---
title: "Excel Workbook Describe"
status: done
phase: P0
---

# Task 03 — Excel Workbook Describe

Implement `spreadsheet_describe(session_id)` to orient the model before any bulk cell reads.

## Scope

- `.xlsx` workbooks opened through the session registry.
- Compact workbook and sheet metadata.
- Basic formula, named range, table, merged-cell, and dimension reporting.
- Source citation URIs.

## Deliverables

`spreadsheet_describe` response should include:

- Workbook metadata:
  - file name
  - file size
  - mtime
  - sheet count
  - warning flags
- Per-sheet metadata:
  - sheet name
  - dimensions / used range
  - hidden state
  - merged ranges count and samples
  - formula count
  - named ranges referencing the sheet
  - Excel tables/ListObjects where available
  - compact sample rows
- Source URIs:
  - `file.xlsx#Sheet!A1:F20`

## Acceptance Criteria

- Describe never dumps an entire sheet.
- Response stays under configured char cap for wide or multi-sheet workbooks.
- Formula-heavy sheets are flagged.
- Merged-cell sheets are flagged.
- Named ranges are included when present.
- Tests cover empty workbook, multi-sheet workbook, formula workbook, and named ranges.

## Product Notes

For bookkeeping/accounting work, describe output should make it easy to find ledgers, transaction tables, summary tabs, assumptions, and outputs without reading full data.

