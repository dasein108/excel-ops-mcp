# Deterministic checks — saas_v1

**Score: 20/20**  ·  workbook `saas.xlsx`  ·  no model in the loop

| id | verdict | note |
|----|---------|------|
| q01_total_rev_y1 | ✅ | 1458480.0 vs 1458480.0 (±0.005rel) |
| q02_total_rev_y5 | ✅ | 3127444.992 vs 3127444.992 (±0.005rel) |
| q03_subs_rev_y5 | ✅ | 2282486.1696 vs 2282486.1696 (±0.005rel) |
| q04_gross_margin_y1 | ✅ | 0.76750699358236 vs 0.7675 (±0.01) |
| q05_ebitda_y1 | ✅ | -36406.4 vs -36406.4 (±0.02rel) |
| q06_first_profitable_month | ✅ | 9.0 vs 9.0 (±0.0) |
| q07_net_income_y1 | ✅ | -102081.912121212 vs -102081.912 (±0.02rel) |
| q08_closing_cash_y1 | ✅ | -51564.4778354978 vs -51564.478 (±0.02rel) |
| q09_lowest_cash_y1 | ✅ | -86975.3068398268 vs -86975.307 (±0.02rel) |
| q10_rev_mix_y1 | ✅ | all match |
| q11_yoy_growth_y2 | ✅ | 0.2 vs 0.2 (±0.005) |
| q12_payroll_pct_rev_y1 | ✅ | 0.5685371071252263 vs 0.5685 (±0.01) |
| q13_infra_cogs_y1 | ✅ | 226044.0 vs 226044.0 (±0.005rel) |
| q14_headcount | ✅ | 20.0 vs 20.0 (±0.0) |
| q15_avg_mrr | ✅ | 28.0 vs 28.0 (±0.001) |
| q16_dashboard_rev_source | ✅ | ['P&L Projection'] contains P&L Projection? |
| q17_churn_assumption | ✅ | 2.5 vs 2.5 (±0.001) |
| q18_net_income_formula | ✅ | formula =B47-B49 / precedents ['B47', 'B49'] |
| q19_churn_is_multiplier | ✅ | formula =Assumptions!B6*Assumptions!B7*B4*Assumptions!B8*Assumptions!B10 |
| q20_cash_nonneg_y1 | ✅ | True vs True |
