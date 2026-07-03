---
title: "Computed Value Resolution"
status: done
scope: excel-only
---

# Computed Value Resolution

Formula cells used to surface their formula string (`=B11+B16+B20`) or `null`, so an
agent could never answer a numeric question ("what is year-5 revenue?") against a
formula-driven workbook. This closes that gap.

## Motivation

`examples/saas.xlsx` is a 5-sheet SaaS financial model (~1000 formulas). Discovery
(`sheets`, `tables`) worked, but every numeric read returned formulas. Root cause:
the engine loaded workbooks with `data_only=False` everywhere and both read surfaces
deliberately kept formula strings (`range_read.py`, `duckdb_engine._region_rows`).

## Design — cached first, recompute fallback

`excel_mcp/values.py :: ValueResolver`:

1. **Cached values (primary).** Load a second view with `data_only=True` and return
   the value the spreadsheet app already computed and saved. Deterministic, no deps.
   Covers any file opened+saved by Excel/LibreOffice (including saas.xlsx).
2. **Recompute fallback (optional).** When a formula has no cached value (files
   authored programmatically by openpyxl), evaluate with the `formulas` library.
   Best-effort, guarded by try/except, gated behind the `recompute` extra. On miss,
   the cell resolves to `null` and flags `computed_value_unavailable`.
3. Literal (non-formula) cells pass through unchanged.

The resolver attaches lazily to the session (`WorkbookSession.value_resolver`).

## Surfaces wired (parity)

- `read-range --include values` / `spreadsheet_read_range` → computed number.
  `--include formulas` still returns formula text.
- `query` / `spreadsheet_query` → `_region_rows` materializes computed values, and
  duckdb column types are inferred from the resolved values so numeric formula
  columns aggregate (`_duckdb_type_from_values`).

## Tests

`tests/test_values.py`:
- Cached path against `saas.xlsx` (Total Revenue Y1 = 87680; Gross Profit Y1 ≈ 1119393.6).
- `formulas`/`--include` interplay.
- Recompute fallback degrades to `null`+warning when the extra is absent, else recomputes.

## Docs

`SKILL.md` (computed-values + matrix-sheet rules), `references/cli-workflows.md`
(read-a-model recipe), `README.md`, `pyproject.toml` (`[recompute]` extra).

## Follow-ups (not in this task)

- Better header handling for matrix/transposed sheets so SQL column names are the
  time axis (jan…year_5) instead of formula-derived garbage. Tracked in task 27.
