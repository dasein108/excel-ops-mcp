---
title: "Region and Header Detection"
status: done
phase: P0
---

# Task 04 — Region and Header Detection

Detect table-like regions within each Excel sheet so SQL queries operate on meaningful tables instead of entire sheets.

## Scope

- Empty-row and empty-column gutter detection.
- Header row inference.
- Region naming.
- Confidence scoring.
- Compact samples per detected region.

## Deliverables

Each detected region should include:

- stable `region_id`
- generated SQL table name
- sheet name
- bounds, for example `A1:F120`
- header row index
- data start row
- row count
- column count
- inferred columns
- confidence score
- `region_kind`, one of:
  - `table`
  - `ledger`
  - `parameters`
  - `summary`
  - `metadata`
  - `unknown`
- source URI

## Header Inference

Use multiple signals:

- non-empty fill rate
- string ratio
- uniqueness
- following-row consistency
- numeric/date density below the candidate header

## Acceptance Criteria

- One clean table is detected as one region.
- Two vertical tables separated by blank rows are detected separately.
- Two horizontal tables separated by blank columns are detected separately.
- Parameter blocks and summary blocks are not mislabeled as transaction ledgers when obvious.
- Tests include messy financial/ops-style sheets with title rows, notes, blanks, and totals.

## Notes

Borrow the contract shape from PSU3D0, but implement the algorithm fresh. Do not copy AGPL code from other projects.

