---
title: "Workbook Fidelity and Regression Fixtures"
status: done
phase: P2
---

# Task 12 — Workbook Fidelity and Regression Fixtures

Build a regression suite that proves the MCP does not damage common Excel workbooks during read/write operations.

## Scope

- Fixture workbooks for common financial/operations cases.
- Byte-level or XML-level checks where practical.
- Formula and formatting preservation checks.
- Warnings for unsupported structures.

## Fixtures

Include workbooks with:

- simple transaction ledger
- multi-table sheet
- formulas
- named ranges
- merged cells
- comments
- hyperlinks
- hidden sheets
- protected sheet
- formatted report
- Excel table/ListObject
- chart-containing workbook

## Acceptance Criteria

- Dry-run does not modify workbook bytes.
- Unrelated cells retain values and formulas after commit.
- Formula cells remain formulas after formula-preserving edits.
- Formatting outside touched ranges survives.
- Unsupported or risky structures produce warnings.
- Regression tests run in CI.

## Notes

`openpyxl` is good enough for many common Excel workflows, but it is not a perfect Excel engine. Fidelity tests are how we keep the product honest.

