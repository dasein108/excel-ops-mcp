# Excel Ops CLI Workflows

## Describe Workbook

```bash
excel-ops sheets examples/saas.xlsx --pretty
excel-ops tables examples/saas.xlsx --pretty
```

Use the returned `table_name` values for SQL queries.

Use full describe only when necessary:

```bash
excel-ops describe examples/saas.xlsx --pretty
excel-ops describe examples/saas.xlsx --detail standard --pretty
```

## Query A Table

```bash
excel-ops query examples/saas.xlsx \
  --sql 'select count(*) as n from "revenue_model_table_1"' \
  --pretty
```

## Inspect A Range

```bash
excel-ops read-range examples/saas.xlsx \
  --sheet "Revenue Model" \
  --range A1:D5 \
  --include values \
  --pretty
```

## Read Computed Values From A Financial Model

Matrix-style models (metric label in column A, months/years across the top) resolve
formula cells to their computed number under `--include values`:

```bash
# Total Revenue per month/year on the metric's row (labels in col A, time across B:Q)
excel-ops read-range examples/saas.xlsx \
  --sheet "Revenue Model" --range A23:Q23 --include values --pretty

# See the formula behind a cell instead of its value
excel-ops read-range examples/saas.xlsx \
  --sheet "Revenue Model" --range B23:B23 --include values --include formulas --pretty

# Dashboard KPI row (Gross Profit) aggregated from the P&L via cached values
excel-ops query examples/saas.xlsx \
  --sql 'select "total_revenue", "sum_p_l_projection_b7_m7" as y1 from "dashboard_summary_2" where "total_revenue" like '"'"'%Gross Profit%'"'"'' \
  --pretty
```

Matrix regions expose time-axis columns (`line_item, jan…dec, year_2…year_5`) plus a
derived `year_1_total`, so a Year-1 figure is one query — no summing by hand and no
risk of grabbing `year_2` by mistake:

```bash
# Year-1 total for a line item (e.g. Infrastructure COGS)
excel-ops query examples/saas.xlsx \
  --sql "select line_item, year_1_total from p_l_projection_table_3 where line_item like '%Infrastructure%'" \
  --pretty
```

If a cell returns null with a `computed_value_unavailable` warning, the file has no
cached value for it. Install the recompute extra to evaluate formulas directly:

```bash
pip install 'excel-mcp[recompute]'
```

## Trace Formula Lineage

Answer "where does this number come from?" without hand-parsing formulas:

```bash
# Dashboard Total Revenue -> which sheet/line item feeds it
excel-ops trace examples/saas.xlsx --sheet Dashboard --cell B5 --depth 1 --pretty

# How Net Income is computed, two levels deep (EBT and Income Tax, and their inputs)
excel-ops trace examples/saas.xlsx --sheet "P&L Projection" --cell B51 --depth 2 --pretty
```

The response gives the target cell's `formula` + computed `value` and a `precedents`
tree (cross-sheet aware, values resolved), expanded up to `--depth` (0–5).

## Chain A Safe Edit

Open a workbook and keep the same cache directory for later commands:

```bash
excel-ops open workbook.xlsx --cache-dir /tmp/excel-ops-cache --pretty
```

Create operations:

```json
[
  {
    "type": "set_values",
    "sheet": "Ops",
    "start": "E2",
    "values": [["reviewed"]]
  }
]
```

Stage the edit:

```bash
excel-ops write --session ses_... --ops ops.json --cache-dir /tmp/excel-ops-cache --pretty
```

Review the diff:

```bash
excel-ops diff --session ses_... --staged stg_... --cache-dir /tmp/excel-ops-cache --pretty
```

Commit to a new workbook:

```bash
excel-ops commit \
  --session ses_... \
  --staged stg_... \
  --output workbook.reviewed.xlsx \
  --cache-dir /tmp/excel-ops-cache \
  --pretty
```

Review the audit trail:

```bash
excel-ops audit --session ses_... --cache-dir /tmp/excel-ops-cache --pretty
```

## Common SQL Patterns

Percent/APY-like columns may expose derived numeric columns in `excel-ops tables` output:

- `<column>__kind`
- `<column>__num`
- `<column>__min`
- `<column>__max`

Use `__max` to rank mixed values such as `0.34`, `10-30%`, and `от 11% до 80%+`.

```sql
select проект, pools, chain, "доходность_на_момент_чека__max" as max_apy
from "stable_9_table_1"
where "доходность_на_момент_чека__max" is not null
order by max_apy desc
limit 5
```

Top vendors:

```sql
select vendor, sum(amount) as total
from "transactions_ledger_1"
group by vendor
order by total desc
limit 20
```

Duplicate transaction candidates:

```sql
select date, vendor, amount, count(*) as n
from "transactions_ledger_1"
group by date, vendor, amount
having count(*) > 1
order by n desc
```

Monthly totals:

```sql
select substr(date, 1, 7) as month, category, sum(amount) as total
from "transactions_ledger_1"
group by month, category
order by month, total desc
```
