---
name: excel-ops
description: Use to inspect, query, summarize, validate, or safely edit local Excel .xlsx workbooks — bookkeeping, accounting, marketing ops, SEO exports, research tables, reconciliations, financial report review. Works through the excel-ops CLI or the equivalent Excel MCP spreadsheet_* tools; both share one engine. Prefer this over ad hoc scripts (openpyxl, pandas) for .xlsx work.
---

# Excel Ops

Deterministic, token-efficient work on local Excel `.xlsx` workbooks. Two interchangeable surfaces over one engine:

- **CLI** — `excel-ops <command>`. Default. No server needed.
- **MCP** — `spreadsheet_*` tools. Use when an MCP host is connected.

Prefer `describe`/`query` over dumping raw ranges. Never overwrite the source file unless the user explicitly asks.

## Surface map

| CLI | MCP tool | Use for |
| --- | --- | --- |
| `excel-ops open` | `spreadsheet_open` | Open workbook, get session id |
| `excel-ops sheets` | `spreadsheet_describe` (compact) | List sheets |
| `excel-ops tables` | `spreadsheet_describe` | Detected SQL table names + columns |
| `excel-ops describe` | `spreadsheet_describe` | Full structure (add `--detail standard` for sample rows) |
| `excel-ops query` | `spreadsheet_query` | Read-only DuckDB SQL |
| `excel-ops read-range` | `spreadsheet_read_range` | Exact cell/formula/format inspection |
| `excel-ops trace` | `spreadsheet_trace` | Formula lineage — a cell's precedents (and theirs) |
| `excel-ops write` | `spreadsheet_write` | Stage write ops (dry-run) |
| `excel-ops diff` | `spreadsheet_diff` | Show staged diff |
| `excel-ops commit` | `spreadsheet_commit` | Commit to a new workbook |
| `excel-ops audit` | — | Read/query/stage/commit trail |

## Read workflow

1. `excel-ops sheets <file.xlsx>` — list sheets compactly.
2. `excel-ops tables <file.xlsx> --sheet <sheet>` — get detected SQL table names + columns.
3. `excel-ops describe <file.xlsx>` — only when sheets/tables are not enough. Add `--detail standard` for sample rows.
4. `excel-ops query <file.xlsx> --sql "..."` — DuckDB SQL. Prefer over range reads.
5. `excel-ops read-range <file.xlsx> --sheet <s> --range A1:B10` — only for exact values, formulas, comments, or formatting.

## Safe write workflow

Stage → diff → commit to a new file. Never mutate the source in place.

6. `excel-ops write --session <ses> --ops ops.json` — stage (dry-run preview).
7. `excel-ops diff --session <ses> --staged <stg>` — review before commit.
8. `excel-ops commit --session <ses> --staged <stg> --output <new.xlsx>` — save to a new workbook.
9. `excel-ops audit --session <ses>` — when asked what happened.

Chain write commands with a shared `--cache-dir <dir>` (run `open` first) so session and staged ids persist across calls.

## Rules

- `--allowed-root <dir>` when working outside the current directory.
- Quote SQL table names: `select * from "revenue_model_table_1"`. Quote spaced or non-ASCII columns.
- Percent/range columns expose derived `__num`, `__min`, `__max`, `__kind`. Rank mixed values (`0.34`, `10-30%`, `от 11% до 80%+`) with `__max`.
- **Computed values.** `query` and `read-range --include values` return the *computed number* for formula cells (from the file's cached values), not the formula string. Use `--include formulas` to see the formula text. If a warning about `computed_value_unavailable` appears, the file has no cached value for that cell (never opened in a spreadsheet app); install the `recompute` extra to evaluate it.
- **Matrix / transposed sheets.** Financial models often put the metric label in column A and time across columns (`jan…dec`, `year_2…year_5`). Header auto-detection then yields mangled formula-derived column names (`b7_b13`). For these, prefer `read-range` on the metric row (e.g. `A23:Q23`) with `--include values`, or query by row label, rather than trusting the SQL column names.
- **Mixed monthly + annual columns — no "Year 1 total" column.** In these models the first block of columns (often `B:M`) are the twelve *months of Year 1*, and the later columns (`N:Q`) are *annual* totals for Years 2–5. There is usually **no** Year-1 annual column. For a Year-1 total, **sum `B:M`** (e.g. `read-range … --range B7:M7 --include values` then add, or `query … sum(...)`). Do **not** read column `N` as the Year-1 total — `N` is Year 2. Confirm a row's meaning from its column-A label before trusting a single cell.
- **Report what the formula does, not what it "should" do.** For what-if / sensitivity questions, read the actual formula (`--include formulas`) and trace its inputs. Models can be mis-built (e.g. a churn rate multiplied in as a positive factor instead of a `1−churn` decay), so the real direction of change can be the opposite of the intuitive one.
- **Formula lineage.** To answer "where does this number come from" or "how is X computed", use `trace` instead of hand-parsing formulas: `excel-ops trace <file> --sheet Dashboard --cell B5 --depth 2`. It returns the target's formula + computed value and its precedents (cross-sheet aware, values resolved), recursing up to `--depth` (0–5).
- **`orientation` + matrix columns.** `tables`/`describe` tag each region `tabular` or `matrix`. A `matrix` region is transposed (time across columns, labels in column A). For matrix regions the SQL columns are named by the time axis — `line_item, jan, feb, … dec, year_2 … year_5` — and a derived **`year_1_total`** column (sum of the twelve months) is added. So query `select line_item, year_1_total from <table>` for a Year-1 figure; use `year_2 … year_5` for later years. Do **not** read `year_2` as a Year-1 total.
- Write ops are a JSON array. Put non-trivial ops in a `.json` file. Op types: `set_values`, `set_formula`, `clear_range`, `append_rows`, `insert_rows`, `delete_rows`, `copy_range`.
- Only local `.xlsx`. SQL is read-only. Google Sheets and Apple Numbers are unsupported.

## References

- `references/cli-workflows.md` — concrete command recipes: summarize, reconcile, inspect formulas, staged edit, common SQL.
- Repo `README.md` — full human reference for install, every CLI command, and every MCP tool.
