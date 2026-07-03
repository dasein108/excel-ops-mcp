---
title: "CLI Usage Recipes for Operations Work"
status: done
phase: P2
---

# Task 19 — CLI Usage Recipes for Operations Work

Create practical command examples for the `excel-ops` CLI and link them from the `excel-ops` skill reference.

## Scope

- Excel-only recipes.
- Command-line workflows.
- Financial operations, bookkeeping, marketing, SEO, research.
- No Google Sheets or Numbers.

## Recipes

Include examples for:

- Describe workbook structure.
- Query a transaction ledger by month/category.
- Find duplicate transactions.
- Find top vendors.
- Summarize campaign performance.
- Rank SEO keywords from an export.
- Inspect formula cells.
- Add a review/status column.
- Stage notes with dry-run.
- Diff staged changes.
- Commit to a new workbook.

## Deliverables

- Update `.codex/skills/excel-ops/references/cli-workflows.md` after the skill exists.
- Add command examples that use real `examples/` workbooks where possible.
- Add at least one generated fixture example for write workflows.

## Acceptance Criteria

- Every recipe uses `excel-ops`, not raw Python.
- Every write recipe includes dry-run, diff, and commit-to-new-file.
- SQL examples quote table names when necessary.
- Recipes are short enough to be loaded as a skill reference.

## Notes

The recipes should teach repeatable behavior, not document every CLI option.

