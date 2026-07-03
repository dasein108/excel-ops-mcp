---
title: "Agent Understandability Rules for Matrix Models"
status: done
scope: excel-only
---

## Shipped

- **Structural matrix columns.** Matrix regions now name their SQL columns by the
  time axis (`line_item, jan…dec, year_2…year_5`) using the sheet's period-header row,
  and add a derived `year_1_total` (sum of the twelve months). Region detection sets
  `data_start_row` to include every metric row. This makes Year-1 questions a single
  query and removes the "grab column N (Year 2) as the Year-1 total" trap
  structurally, not just by rule. (`regions._sheet_period_row/_is_matrix_region/`
  `_matrix_columns/matrix_month_columns`, `duckdb_engine._add_year1_total`.)

- **Matrix orientation** — region detection tags each region `tabular` | `matrix`
  (`regions._orientation`, `RegionInfo.orientation`, surfaced in `tables`/`describe`).
  The saas.xlsx time-axis strips (Revenue Model / P&L / Cash Flow) flag `matrix`.
- **Formula lineage tool** — `spreadsheet_trace` / `excel-ops trace` (`trace.py`):
  given a cell, returns its formula + computed value and a cross-sheet precedents
  tree, recursing to `depth` (0–5). Answers use-cases 11/16 and eval q16/q18 in one
  call. Full MCP+CLI parity, tests (`tests/test_trace.py`), docs.
- **Skill rules** — SKILL.md: mixed monthly+annual columns (no Year-1 total column;
  sum B:M; column N is Year 2), report-what-the-formula-does, and `orientation`/`trace`.

## Remaining

Nothing blocking. Possible follow-ups: a transitive precedents-and-dependents view
in `trace`, and period detection for non-calendar layouts (weeks, fiscal quarters).

# Agent Understandability Rules for Matrix Models

`saas.xlsx` exposed structural patterns that confuse agents even after computed
values landed (task 24). This task hardens region/header detection and the skill
rules so an agent reliably understands transposed financial models.

## Findings from `saas.xlsx`

1. **Transposed layout.** Metric label in column A; time (`jan…dec`, `year_2…year_5`)
   across the top. Header auto-detection picks the month row but derives SQL column
   names from formula cells → `b7_b13`, `assumptions_b52_10`, `if_b47_0_...`. Those
   are unusable as query columns.
2. **Cross-sheet lineage.** Formulas reference other sheets (`revenue_model_b11`,
   `p_l_projection_b51`). Useful for "where does X come from" but not surfaced as a
   first-class relation.
3. **Stacked parameter blocks.** The Assumptions sheet is 12 small key/value tables;
   already handled well by region detection.

## Work items

### A. Detect transposed/time-series regions
- Heuristic: first data row is month/period tokens AND column A is text labels →
  mark region `orientation: "matrix"` in `RegionInfo`.
- For matrix regions, name columns from the time axis (`jan`, `feb`, … `year_5`) and
  expose the label column as `metric`/`line_item`, instead of formula-derived names.
- Keep the raw addresses available for exact reads.

### B. Skill rules (partially shipped in task 24)
- Already added: "Matrix / transposed sheets" rule pointing agents to row reads.
- Extend once (A) lands: document querying matrix regions by `metric` + time column.

### C. Optional: formula lineage helper
- A `describe`-level or new read that, for a target cell, lists the cells/sheets it
  depends on (one hop, or transitive with a depth cap). Answers use-case 11/16 and
  eval questions q16/q18 without the agent hand-parsing formulas.
- Parity: MCP tool + CLI subcommand + skill recipe + tests (per AGENTS.md).

## Acceptance

- Matrix regions in `saas.xlsx` report time-axis column names, queryable by month/year.
- Eval questions q01–q13 answerable via SQL on named time columns (not just row reads).
- If the lineage helper is built, q16/q18 answerable via one tool call.

## Depends on

- Task 24 (computed values). Feeds Task 26 gold accuracy and Task 25 scores.
