---
title: "SaaS Model Eval Suite (20 Questions + Gold)"
status: draft
scope: evals
---

# SaaS Model Eval Suite — `saas_v1`

The concrete 20-question suite for `examples/saas.xlsx`, derived from the top-20 human
use cases. Lives at `evals/saas_v1/`.

## Question set (id → question → gold source)

Read / KPI (numeric, tolerant match):

1. `q01_total_rev_y1` — Total revenue in Year 1? → `'Revenue Model'!B23:M23` summed / Dashboard.
2. `q02_total_rev_y5` — Total revenue in Year 5? → Dashboard revenue row, Year 5 col.
3. `q03_arr_exit` — Exit ARR (final month MRR × 12 or model's ARR line). → Revenue Model.
4. `q04_gross_margin_y1` — Gross margin % in Year 1? → Dashboard Gross Margin % row.
5. `q05_ebitda_y1` — EBITDA in Year 1? → `'P&L Projection'!B36:M36` / Dashboard.
6. `q06_first_profitable_month` — First profitable month? → Dashboard `first_profitable_month_name`.
7. `q07_net_income_y1` — Net income in Year 1? → `'P&L Projection'!B51:M51`.
8. `q08_closing_cash_y1` — Closing cash balance end of Year 1? → `'Cash Flow'!M29`.
9. `q09_lowest_cash` — Lowest monthly closing cash in Year 1 (runway risk)? → min over Cash Flow row 29.
10. `q10_rev_mix_y1` — Subscription vs services vs usage revenue split, Year 1? → Revenue Model rows 11/16/20.
11. `q11_yoy_growth_y2` — YoY revenue growth Year 2? → Assumptions B27 / computed.
12. `q12_payroll_pct_rev_y1` — Payroll as % of Year-1 revenue? → P&L payroll ÷ revenue.
13. `q13_infra_cogs_y1` — Infrastructure COGS in Year 1? → `'P&L Projection'!B9:M9`.
14. `q14_headcount` — Total headcount in the plan? → `Assumptions!` headcount table sum.
15. `q15_avg_mrr` — Average MRR per customer assumption? → `Assumptions!B11`.

Trace / explain (text match or source-ref check):

16. `q16_dashboard_b5_source` — What feeds Dashboard Total Revenue (B5)? → formula lineage to P&L row 7.
17. `q17_churn_assumption` — Monthly churn rate assumption? → `Assumptions!` subscriptions table.
18. `q18_explain_net_income_formula` — How is Net Income computed? → `=EBT - Income Tax` (`b47_b49`).

What-if (safe-write, verified by re-read):

19. `q19_churn_bump_impact` — If churn 2.5%→3.0%, does Year-1 total revenue fall? (stage→commit→re-read, expect lower).
20. `q20_validation_cash_nonneg` — Is closing cash ever negative in Year 1? (validation check over Cash Flow row 29).

## Gold format (`gold.jsonl`)

```json
{"id": "q01_total_rev_y1", "expected": 1319914.9, "unit": "USD", "tolerance": 0.01, "match": "relative", "source_ref": "saas.xlsx#'Revenue Model'!B23:M23"}
{"id": "q06_first_profitable_month", "expected": "Aug", "match": "enum", "source_ref": "saas.xlsx#Dashboard!B15"}
{"id": "q16_dashboard_b5_source", "expected": ["P&L Projection", "row 7", "Total Revenue"], "match": "contains_all", "source_ref": "saas.xlsx#Dashboard!B5"}
```

- `match`: `relative` | `absolute` | `enum` | `contains_all` | `judge`.
- Numbers computed **only** via `excel-ops` (computed values from task 24), never
  hand-typed, so gold is reproducible.

## Build steps

1. For each numeric question, run the documented `excel-ops query`/`read-range`
   command; capture the value into `gold.jsonl` with a source_ref.
2. For trace questions, capture the expected lineage tokens / formula.
3. For what-if questions, record the expected direction of change (and the committed
   output workbook path for the answerer to re-read).
4. Commit `questions.jsonl` + `gold.jsonl`. Human review before first eval run.

## Acceptance

- 20 questions in `questions.jsonl`, 20 gold rows in `gold.jsonl`.
- Every gold value regenerable by re-running its recorded excel-ops command.
- Suite runs green through task 25's harness with a target score threshold (e.g. ≥18/20).

## Depends on

- Task 24 (computed values), Task 25 (harness).
