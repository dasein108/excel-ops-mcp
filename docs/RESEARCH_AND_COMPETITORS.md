---
title: "Excel MCP — Research & Competitor Landscape"
status: reference
---

# Excel MCP — Research & Competitor Landscape

Background research that informed this project's design, in two parts:

- **Part I — Competitor landscape.** A survey of 15+ open-source Excel/spreadsheet
  MCP servers: what each does well, where they fall short, and which design ideas
  are worth borrowing.
- **Part II — Architecture review.** A deeper, DuckDB-aware comparison (MotherDuck
  MCP vs PSU3D0 vs an in-house hybrid) and the reasoning behind the architecture
  this repository implements.

> **Provenance.** These two reports were written during an originating investigation
> for a larger product. Some cross-references — `EXCEL_USAGE_REVIEW.md`,
> `PROBLEM_CATEGORIES.md`, `SUMMARY.md`, and `tasks/NN-xls-*.md` specs — point at
> that investigation and are **not** included in this repository; they are retained
> for context. This repo is a standalone implementation of the "Architecture C"
> ideas argued for below: **DuckDB SQL reads over detected regions, workbook
> sessions, and a stage → diff → commit write contract** (see the root
> [README](../README.md)).

---

# Part I — Competitor Landscape


## Excel/xlsx MCP Server Landscape — Research Report

**Audience:** DC team designing new xlsx tool stack to fix N+1 reads, verbose output, and missing cache.
**Date:** 2026-05-06
**Scope:** Open-source MCP servers that read/write Excel or spreadsheet files.

---

### TL;DR

- **15 distinct projects reviewed.** Most are demo-grade thin wrappers around openpyxl or SheetJS that return raw rows — they actively cause the very problems we are trying to fix.
- **Three are designed around our exact problem space:** `jwadow/mcp-excel` (AGPL, atomic ops + LRU cache + header detection), `marekrost/mcp-server-spreadsheet` (MIT, DuckDB SQL, atomic save, multi-format), and `PSU3D0/spreadsheet-mcp` (Apache-2.0, Rust, region detection + sessions + verification).
- **One DuckDB-based MCP exists for spreadsheets:** `marekrost/mcp-server-spreadsheet`. It maps every sheet to a DuckDB table, supports JOINs across sheets, and persists mutations back via openpyxl — almost exactly what Task 28 specifies.
- **One project does multi-table-per-sheet detection:** `PSU3D0/spreadsheet-mcp` — vertical and horizontal gutter splits with explicit `bounds`, `header_row`, and `region_kind` (Data / Table). Tests prove it works.
- **One project has explicit per-process file caching with TTL + memory cap:** `jwadow/mcp-excel` (LRU, 5 files, 1 GB cap, 10-min idle).
- **None ship our exact stack** (exceljs + DuckDB + multi-table detection + per-chat tool-result cache + reversibility primitive). Building Tasks 24/28/29 remains the right call. We should steal ideas, not adopt wholesale.

---

### 1. Comparison Table

Mature read+write MCP servers, ranked by overall design fit for our three problems.

| Name | Stars | Lang / Engine | Read tools | Write tools | Multi-sheet | Multi-table-per-sheet | SQL/DSL | Token-cost shape | Caching | License | Last push |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **PSU3D0/spreadsheet-mcp** | 44 | Rust / umya-spreadsheet + formualizer | `read sheets/overview/values/cells/page/table/names/workbook/layout/export` | `write cells/import/append/clone-template-row/clone-row-band/formulas replace/name/batch transform/style/formula-pattern/structure/...` | Yes | **Yes (gutter detection, tested)** | Custom JSON ops, no SQL | **Region overview first, exact-cell inspection, layout-aware. Explicit pagination with `next_start_row`, `next_offset`. Bounded compact reads.** | Yes (LRU, sessions with fork/undo/redo) | Apache-2.0 | 2026-05-06 |
| **marekrost/mcp-server-spreadsheet** | 2 | Python / openpyxl + DuckDB + odfpy | `read_sheet/read_cell/read_range/get_sheet_dimensions/search_sheet/list_sheets/describe_table/sql_query` | `write_cell/write_range/append_rows/insert_rows/delete_rows/clear_range/copy_range/insert_columns/delete_columns/sql_execute` | Yes | No (sheet=table only) | **DuckDB SQL across sheets with JOIN, GROUP BY, aggregates, subqueries. `sql_execute` writes back** | `describe_table` returns columns + types + row count + 3 sample rows. `read_sheet` returns full 2D array on demand. SQL returns aggregated rows only. | No (loads workbook on every call) | MIT | 2026-03-08 |
| **jwadow/mcp-excel** | 31 | Python / pandas + openpyxl + psutil | `inspect_file/get_sheet_info/get_column_names/get_data_profile/find_column/search_across_sheets/compare_sheets`, 12 filter operators, 8 aggregations, group_by, correlations | None for Excel writes — read/analyze only | Yes | No (header detection per sheet) | Operation DSL (filter/aggregate/groupby/rank/timeseries) — backed by pandas, not SQL | **Atomic operations return counts/sums/formulas, not rows. Sample rows capped to 3. "Hard cap of 500 rows per call".** Returns Excel formulas alongside values for traceability. | **Yes — LRU FileCache, 5 files / 1 GB / 10-min idle, key includes mtime.** | **AGPL-3.0** | 2026-02-28 |
| **haris-musa/excel-mcp-server** | 3789 | Python / openpyxl | `read_data_from_excel/get_workbook_metadata/get_data_validations` | `write_data_to_excel/apply_formula/format_range/create_chart/create_pivot_table/create_table/copy_sheet/...` | Yes | No | No | **Returns raw 2D values plus per-cell metadata as pretty-printed JSON. No paging cap. `read_data_from_excel` will dump entire used range if `end_cell` omitted.** This is the antipattern. | No | MIT | 2026-04-12 |
| **negokaz/excel-mcp-server** | 942 | Go / excelize + OLE on Windows | `excel_describe_sheets/excel_read_sheet/excel_screen_capture` | `excel_write_to_sheet/excel_create_table/excel_copy_sheet/excel_format_range` | Yes | No | No | **Returns HTML tables. Has `EXCEL_MCP_PAGING_CELLS_LIMIT` (default 5000 cells/page); next-range hint embedded.** Better than haris-musa but still bytes-heavy. | No | MIT | 2025-07-19 |
| **sbroenne/mcp-server-excel** | 149 | C# / Excel COM | 23 tools / 230 ops covering Power Query, DAX, PivotTables, Charts, VBA, Conditional Formatting | Same — full COM | Yes | No | No (DAX yes, but DAX is an output not a read DSL) | Returns raw COM range data; no compact form documented. | Per-Excel-process | MIT | 2026-04-29 |
| **knowledgestack/ks-xlsx-parser** | 17 | Python lib (used as MCP) / openpyxl + xxhash | `parse_workbook` returns chunks with `source_uri`, formulas, deps, charts, conditional formatting | None — read-only | Yes | Partial (tables/ListObjects detected, not arbitrary tables) | No | **Token-counted RAG chunks with citation URIs (`file.xlsx#Sheet!A1:F18`).** Chunked + bounded by design. | xxhash content addressing for dedup | MIT | 2026-04-25 |
| **ArchimedesCrypto/excel-reader-mcp** | 29 | Node.js / SheetJS | `read_excel` (single tool) | None | Yes | No | No | **Auto-chunks at 100 KB with `nextChunk` hint.** Read-only; no schema-first. | No | MIT | 2026-03-12 |
| **jonemo/openpyxl-mcp-server** | 19 | Python / openpyxl | `get_cell_details/get_cell_value/get_values_of_cell_range/get_content_of_cell_list/search_in_cell_range/get_list_of_sheets` | None | Yes | No | No | Cell-by-cell only — verbose per-cell text dump (font/fill/etc.). 356 lines total — **thin wrapper.** | No | MIT | 2026-05-02 |
| **yzfly/mcp-excel-server** | 89 | Python / pandas + matplotlib | `read_excel/get_excel_info/get_sheet_names/analyze_excel/filter_excel/pivot_table/data_summary` | `write_excel/update_excel/export_chart` | Yes | No | No (pandas DSL) | Returns pandas summaries (describe()) plus full data on demand. | No | None / unspecified | 2025-05-05 |
| **guillehr2/Excel-MCP-Server-Master** | 28 | Python / openpyxl + Node.js launcher | `read/write/charts/pivot/import-export csv/json/sql/pdf` | Same | Yes | No | No | Standard openpyxl 2D dumps with pagination flag. Generic. | No | MIT | 2025-06-18 |
| **mort-lab/excel-mcp** | 5 | Python / openpyxl + Pydantic | 20 tools across workbook/sheet/cell/format | Same | Yes | No | No | Standard openpyxl per-cell or per-range. Pydantic-validated. | No | MIT | 2025-10-29 |
| **jgravelle/jdatamunch-mcp** | 55 | Python / SQLite + streaming parser | `index_local/describe_dataset/describe_column/get_rows/aggregate/join_datasets/get_correlations/get_distribution/search_data/run_sql/sample_rows/plan_query/...` | None for source — index-then-query model | Yes (one dataset per file) | No | **SQLite-backed SQL. `run_sql` is parameterised, all aggregations server-side.** | **Schema-first by design. Hard 500-row cap. Token budget enforced (default 8000). Anti-loop detection. Wide-table auto-pagination at 60 cols.** Reports `tokens_saved` per call. | **Persistent SQLite index with HEAD-SHA invalidation.** | **Dual-licensed: AGPL-style "free for personal use", commercial requires paid license.** | 2026-05-04 |
| **ZephyrDeng/spreadsheet-mcp** | 11 | TypeScript / SheetJS + papaparse | `view/filter/sort` | `update_xlsx/add_sheet` | Yes (xlsx) | No | No | Returns 2D arrays as JSON strings. Compact-ish but no schema-first. | No | MIT | 2025-04-22 |
| **xing5/mcp-google-sheets** | 847 | Python / Google API | Read/write Google Sheets only | Same | Yes | No | No | Google API directly. Out of scope (cloud-only) but listed for completeness. | No | MIT | 2026-05-07 |

---

### 2. Per-MCP Capsules

#### PSU3D0/spreadsheet-mcp (Apache-2.0, Rust, 44 stars)
The most architecturally thoughtful project in the field. Built as a kit with four surfaces: CLI (`asp`), MCP server (stateful), JS SDK, and WASM. Uses `umya-spreadsheet` for parsing and `formualizer` for native recalc. The crown jewels for our use case are: (a) **region detection** — `read overview` returns multiple `RegionKind::Data | Table` entries with `bounds: "A1:B3"`, `header_row`, and gutter-based splitting (vertical and horizontal), proven by `tests/region_detection.rs`; (b) **explicit pagination contracts** with `next_start_row` and `next_offset`; (c) **session model** with fork/undo/redo/checkout/materialize; (d) **verification primitives** — `verify diff`, `verify proof`, `analyze ref-impact` for previewing structural impact before mutating; (e) **dry-run on every mutation** with strict `--dry-run`/`--in-place`/`--output` matrix. Does NOT solve N+1 directly (no per-chat dedup) but the structural read commands (`overview`, `cells`, `layout`) replace bulk re-reads with targeted exact lookups. Does solve verbose-output (compact bounded reads, layout-only when needed). Does NOT solve model-swap re-probe specifically (state lives per-session, not per-chat-id). 179 Rust files, sophisticated test coverage, weekly releases. The barrier to adoption: Rust embedding from our Electron stack means shipping a binary, plus the CLI/session model is heavyweight relative to our minimal three-tool target.

#### marekrost/mcp-server-spreadsheet (MIT, Python, 2 stars)
Tiny on stars but **closest to our Task 28 design**. Pure Python, hatchling-built, `uvx` runnable. Three killer tools: `describe_table` (columns + DuckDB-inferred types + row_count + 3 sample rows — schema-first), `sql_query` (read-only DuckDB SELECT with JOINs across sheets), `sql_execute` (DuckDB INSERT/UPDATE/DELETE that writes back via openpyxl). Each call loads the workbook into an in-memory DuckDB DB built on the fly with type inference (BIGINT/DOUBLE/VARCHAR/TIMESTAMP/DATE coalesced from row values), header dedup with `_N` suffixes, and atomic save (`os.replace()`). Multi-format: `.xlsx` via openpyxl, `.csv` via stdlib, `.ods` via odfpy. Solves verbose-output (SQL aggregation, not raw rows). Does NOT solve N+1 (loads workbook on every call — no cache). Does NOT solve multi-table-per-sheet (treats sheet=table; bad if file has staking blocks separated by gutters). Does NOT solve model-swap re-probe. **Critical strength: the SQL engine is exactly what we want for Task 28.** The whole server is ~750 lines of one file. Highly forkable.

#### jwadow/mcp-excel (AGPL-3.0, Python, 31 stars)
**The only project that explicitly markets itself against the exact problems in our review.** Tagline: "no data dumping into AI context." Atomic operations (filter_and_count, aggregate, group_by, correlations, time-series, ranking) return numbers/formulas, not rows. Multi-criteria filters with 12 operators and nested AND/OR. Built-in **header detection** with confidence scoring (fill rate + uniqueness + string-ratio + following-row consistency) — directly applicable to our messy financial-model use case. **Explicit FileCache** (LRU, 5 files, 1 GB memory cap, 10-minute idle eviction, mtime-keyed) — solves N+1 at the Python-process level for the same Python process. Strong test surface (~50 test files including smoke + integration + unit). Does NOT do writes (read/analyze only). Does NOT do multi-table-per-sheet. Does NOT solve cross-chat or model-swap re-probe (cache is per-process). **AGPL-3.0 is a hard blocker** — Desktop Commander ships closed binaries; AGPL would require open-sourcing the whole Electron app or replacing this layer. The header-detection algorithm is open-source and we can re-implement it under our own license.

#### haris-musa/excel-mcp-server (MIT, Python, 3789 stars)
The most-installed Excel MCP. Uses openpyxl. 25+ tools covering everything the README promises (formulas, charts, pivot tables, formatting, validation, sheet ops). `read_data_from_excel` calls `read_excel_range_with_metadata` and **returns `json.dumps(result, indent=2)` of every cell with `address`, `value`, `row`, `column`, validation` — for an entire used range when `end_cell` is omitted**. This is the design that produces our 141 KB token-bloat traces. No pagination cap, no schema-first mode, no caching. Solves none of our problems; in fact, this server's response shape is approximately what we already have. Useful as proof that "lots of stars" does not mean "good for our use case."

#### negokaz/excel-mcp-server (MIT, Go, 942 stars)
Backed by `excelize` (or COM/OLE on Windows). **Has built-in pagination** via `EXCEL_MCP_PAGING_CELLS_LIMIT` (default 5000 cells per page) — calculated by `pageSize / totalCols` rows per page, with a `nextRange` pointer embedded in every response. Returns **HTML tables**. Style and formula reads are flag-gated (`showStyle`, `showFormula`). Does not do schema-first, multi-table detection, SQL, or caching. The pagination model is the simplest battle-tested pattern in the field — useful reference for our sub-call paging if we keep `read_file(xlsx)`.

#### sbroenne/mcp-server-excel (MIT, C#, 149 stars)
Windows-only. Drives Excel via COM API (so requires Excel installed and running on a desktop). 230 operations including Power Query, DAX, VBA — power features outside our scope. Notable for marketing **"64% fewer tokens"** with their CLI variant vs MCP — they argue the MCP schema bloat itself is a token cost. Validates with `pytest-skill-engineering` — first project I saw doing LLM-side test validation. Out of scope for us (Windows + Excel install required), but the "test that LLMs use the tool correctly" idea is worth borrowing for our regression suite.

#### knowledgestack/ks-xlsx-parser (MIT, Python lib, 17 stars)
Not strictly an MCP server — it is a Python library that ships an MCP-compatible interface. Parses `.xlsx` into typed JSON with citation URIs (`file.xlsx#Sheet!A1:F18`), token-counted RAG chunks, dependency graph (formula precedents/dependents), all 7 chart types, conditional formatting rules, ListObjects/tables, merged regions. xxhash64 content addressing. Good design pattern: **"chunk a workbook, give every chunk a citation URI."** Does not solve write or interactive workflows, but the chunk-with-URI pattern is exactly the response shape we want for `read_file(xlsx)` deprecation: every read returns chunks with `source_range` so the model can cite exactly what it used.

#### ArchimedesCrypto/excel-reader-mcp (MIT, Node.js, 29 stars)
SheetJS-based, single tool `read_excel`, automatic 100 KB chunking with `hasMore` and `nextChunk`. Read-only. No schema-first, no SQL, no caching. The chunking + nextChunk shape matches negokaz; both are basic but shippable. Technical merit: shows the simplest possible "just don't blow up" implementation.

#### jonemo/openpyxl-mcp-server (MIT, Python, 19 stars)
**Thin wrapper** — single 356-line Python file. Cell-by-cell: `get_cell_details` returns ~20 lines of text per cell (font, fill, hyperlink, comment). Useful as a reference for "exact cell inspection" tool design but does no batching. No write tools.

#### yzfly/mcp-excel-server (no license, Python, 89 stars)
Pandas-based with matplotlib chart export. Has `data_summary` (a pandas describe() wrapper). **No license file** — discount entirely. Last push 2025-05.

#### guillehr2/Excel-MCP-Server-Master (MIT, Python, 28 stars)
Generic openpyxl wrapper, npm-distributed. Imports/exports CSV/JSON/SQL/PDF. Standard 2D dumps. Last push June 2025. No notable design choices.

#### mort-lab/excel-mcp (MIT, Python, 5 stars)
20 tools, Pydantic-validated. Generic openpyxl. Tested (17 tests). Production-readiness limited by openpyxl's own write-side limitations (loses charts/comments unless `keep_vba=True`).

#### jgravelle/jdatamunch-mcp (dual-licensed: free non-commercial / paid commercial, Python, 55 stars)
**Designed for the exact token problem we have, but for tabular data generally.** Indexes CSV/Excel/Parquet/JSONL into a persistent SQLite store at `~/.data-index/`. Profiles every column once (HLL, t-digest, BM25, semantic types, null patterns). Tools: `describe_dataset` (schema), `describe_column` (per-column stats), `get_rows` (filtered, capped at 500), `aggregate` (server-side GROUP BY in SQLite), `join_datasets` (SQL JOIN via `ATTACH DATABASE`), `get_correlations` (pairwise Pearson), `run_sql` (parameterised). **Built-in token-budget enforcement (default 8000), anti-loop detection (warns if agent paginates row-by-row), wide-table auto-pagination at 60 cols, per-call `tokens_saved` telemetry.** Documents 25,333× token reduction on a 1M-row CSV vs raw paste. Does NOT do writes (one-way: source → index → answer). **Commercial license required for revenue use** ($39+/seat) — that plus AGPL-style restriction is a compliance risk for DC. The architectural patterns (persistent index, schema-first, anti-loop, token telemetry) are all open-source and we can lift them.

#### ZephyrDeng/spreadsheet-mcp (MIT, TypeScript, 11 stars)
View/filter/sort/update — basic. SheetJS + papaparse. No SQL, no caching, no schema-first. Not relevant.

#### xing5/mcp-google-sheets (MIT, Python, 847 stars)
Google Sheets API only — out of scope. Listed because it tops the "spreadsheet mcp" search rankings.

#### chrisryugj/kordoc (MIT, Node.js, 896 stars)
Korean-government-document focused. Parses HWP/HWPX/PDF/XLSX/DOCX → Markdown. Strong on tables in scanned PDFs and HWP, only basic XLSX support. Out of scope but worth noting for the Markdown-first response shape.

---

### 3. Synthesis — Specific Questions

#### Is there an existing MCP we could adopt wholesale to skip building Tasks 24/28/29?

**No.** Closest candidates and why each fails:

- **PSU3D0/spreadsheet-mcp** has region detection, recalc, sessions, verification — superset of our design — but is Rust, ships a binary CLI (`asp`), and embeds a heavyweight session model that doesn't fit our "three-tool minimal" goal. We'd be adopting an entire spreadsheet-automation kit, not a tool stack.
- **marekrost/mcp-server-spreadsheet** has the exact Task 28 SQL engine (DuckDB) and atomic writes, but no caching, no multi-table-per-sheet, sheet-name-as-table-name only. Need to extend in 2-3 directions.
- **jwadow/mcp-excel** has caching + header detection but no writes, and AGPL-3.0 makes it a non-starter for our shipping model.
- **jgravelle/jdatamunch-mcp** has the indexing + token-budget + anti-loop telemetry we want but is read-only and commercially restricted.

#### Is there one we could adopt partially?

**Yes, three.** Strongest fit:

1. **Fork or vendor `marekrost/mcp-server-spreadsheet`'s DuckDB layer.** ~750 lines, MIT, single file. The `_sheet_to_records` + `_dedup_headers` + `_infer_duckdb_type` + `_load_sheets_to_duckdb` stack is exactly our Task 28 — we'd add multi-table-per-sheet detection in front of `_sheet_to_records` and add per-chat caching around `load_workbook`. Saves us 1-2 weeks vs writing the SQL plumbing ourselves.

2. **Re-implement `jwadow/mcp-excel`'s `HeaderDetector` algorithm under MIT** (we cannot copy AGPL code into our codebase, but algorithms are not copyrightable). The four signals (fill rate, uniqueness, string ratio, following-row consistency with low variance) are all clearly described and easy to re-derive.

3. **Borrow `PSU3D0/spreadsheet-mcp`'s region-detection contract** — explicit `bounds`, `header_row`, `region_kind: Data | Table` per region — for our `xls_describe` response shape. We don't need their gutter algorithm if exceljs + a basic empty-row/empty-column detector gives us 90% — but the response schema is well-considered.

#### Are there features in some MCP we should add to our design that we hadn't thought of?

Yes, several:

- **Token-saved telemetry per call.** jdatamunch reports `tokens_saved` and `cost_avoided` per response and has a session-level `get_session_stats`. This would directly validate our project to Dmitry and Richard with hard numbers post-launch instead of needing post-hoc PostHog analysis.
- **Anti-loop detection.** jdatamunch warns when an agent is paginating row-by-row in a tight loop. This is structurally similar to our N+1 same-file-read problem and could be a generic alert across all our tools.
- **Citation URIs in every read response** (ks-xlsx-parser pattern). Every chunk we return should carry a `source_range: "file.xlsx#Sheet!A1:F18"` so the model can reference what it used. Good for trust and debuggability, low cost to add.
- **`ref-impact` / dry-run preflight before mutations** (PSU3D0). For `xls_write`, return what cells would change without writing, so the model can verify intent before committing.
- **Wide-table auto-pagination.** jdatamunch caps at 60 columns per `describe_dataset`. Worth adding to `xls_describe` for genuinely wide financial models.
- **`compare_sheets` / schema_drift** (jwadow + jdatamunch). When the same file is updated and a model re-reads it, returning a diff against the cached version is much cheaper than a full re-read. Pairs naturally with our Task 08 cache.
- **CSV/ODS coverage in the same tool** (marekrost). Treating CSV as a single-sheet workbook means one tool stack for `.xlsx`, `.csv`, `.ods` — simpler model-facing surface than separate tools.
- **`fileAbsolutePath` mtime in cache key** (jwadow). Prevents stale-cache bugs when the file changes between calls. Should be in our Task 08 cache key.
- **Sandboxing via `EXCEL_FILES_PATH`** (haris-musa). Good security pattern when the MCP runs in a less-trusted context — refuses absolute paths and `..` traversal.

#### What is the "best in class" by language?

- **Best Python:** `marekrost/mcp-server-spreadsheet` (MIT) for read+write+SQL, or `jwadow/mcp-excel` if AGPL acceptable for read-only analysis. `jgravelle/jdatamunch-mcp` is the best architectural reference but is restricted-license.
- **Best Node.js:** None genuinely good. `ZephyrDeng/spreadsheet-mcp` and `ArchimedesCrypto/excel-reader-mcp` are both basic. Notable gap in the ecosystem — Node.js ones are uniformly thin wrappers around SheetJS.
- **Best Go:** `negokaz/excel-mcp-server` (MIT, 942 stars) — solid pagination via excelize, well-documented.
- **Best Rust:** `PSU3D0/spreadsheet-mcp` — the only mature Rust entry, and architecturally the strongest overall.
- **Best for non-token-bloat:** `PSU3D0/spreadsheet-mcp` > `marekrost/mcp-server-spreadsheet` > `jwadow/mcp-excel` > `jgravelle/jdatamunch-mcp`.

#### Any MCP using DuckDB?

**Yes, exactly one for spreadsheets: `marekrost/mcp-server-spreadsheet`.** Pattern to study:
- One DuckDB connection per tool call (in-memory, ephemeral).
- Each sheet is loaded as a table named `"<SheetName>"` (double-quoted to allow spaces).
- Per-column type inference from data: empty=VARCHAR, single-type=that type, mixed BIGINT+DOUBLE=DOUBLE, anything else mixed=VARCHAR.
- Header dedup with `_1`, `_2` suffixes.
- For mutations: `_extract_target_table(sql)` regex-parses the target table from `INSERT INTO`/`UPDATE`/`DELETE FROM`, runs SQL, then writes the modified table back to the sheet via openpyxl. Atomic via temp file + `os.replace()`.

Watch-outs: (1) reload cost — they load the whole workbook on every SQL call; we should keep our cache in front. (2) sheet=table mapping fails for multi-table sheets; we'd need to pre-process with our region detector and expose each region as a separate table (e.g. `"Sheet1.region_1"`, `"Sheet1.region_2"`). (3) DuckDB will accept Excel's funky header characters fine inside double quotes but column references in SQL get awkward.

`jgravelle/jdatamunch-mcp` uses **SQLite**, not DuckDB. Worth noting but DuckDB is the better choice for our analytical workloads.

`motherduckdb/mcp-server-motherduck` (476 stars) is the canonical DuckDB MCP but it operates on `.duckdb` files, not Excel — out of scope but useful API reference for SQL-MCP ergonomics.

#### Any MCP that does multi-table-per-sheet detection?

**Yes, exactly one: `PSU3D0/spreadsheet-mcp`.** Algorithm characteristics inferred from `tests/region_detection.rs`:
- Detects single tables with no gutters.
- Splits a sheet into multiple regions when separated by **vertical gutters** (empty rows between blocks) — test case: rows 1-3 + rows 6-8 → two regions.
- Splits horizontally on column gutters (test case `two_tables_horizontal_gutter`).
- Each region carries `bounds: "A1:B3"`, `header_row: Some(1)`, `region_kind: Data | Table`.
- The detection is part of `WorkbookContext::get_sheet_metrics(sheet).detected_regions()`.

We can re-implement the gutter heuristic in TypeScript/exceljs in a few hundred lines: slide a window across rows looking for fully-empty rows that separate non-empty bands, same across columns. PSU3D0's tests are good fixtures to copy for validation.

`knowledgestack/ks-xlsx-parser` detects ListObjects (Excel-defined tables) but not arbitrary visual tables.

#### Any MCP that solves the N+1 / repeated-read problem with caching?

**At the per-process level, yes:**

- **`jwadow/mcp-excel`** has explicit `FileCache` — LRU, max 5 files, 1 GB memory cap, 10-minute idle TTL, key includes `mtime`. This is the right pattern but only works within one Python process running multiple tool calls, not across Electron tool invocations on different MCP server processes.
- **`PSU3D0/spreadsheet-mcp`** has session-level workbook caching with fork/checkout/materialize.
- **`jgravelle/jdatamunch-mcp`** has persistent SQLite indexes at `~/.data-index/` with HEAD-SHA invalidation. Survives across runs.

**None solve the cross-chat / model-swap case** (our "same xlsx re-probed 9× across model swaps" problem). That's because none of them know about the chat ID — they cache by file + mtime within process. Our Task 08 (per-chat tool-result cache keyed by `tool_name + args_hash + chat_id` and persisted in SQLite) is uniquely positioned.

#### Any MCP that returns schema-first instead of bytes?

**Yes, several, with varying quality:**

- **Best:** `jgravelle/jdatamunch-mcp` `describe_dataset` — column names, types, cardinality, null rates, value distributions, histogram, samples. All in one sub-10 ms call. Schema before any rows.
- **Strong:** `marekrost/mcp-server-spreadsheet` `describe_table` — columns + types + row count + 3 sample rows. Single call. Exactly the shape we want for `xls_describe`.
- **Strong:** `jwadow/mcp-excel` `inspect_file` + `get_sheet_info` — file structure, sheet rows/cols, column types, header detection confidence, sample rows.
- **Good:** `PSU3D0/spreadsheet-mcp` `read overview` — region-aware structural overview before any cell reads.
- **Antipattern:** `haris-musa/excel-mcp-server`, `negokaz/excel-mcp-server` — start by giving the model raw cell values; no schema-first option.

---

### 4. Problem-by-Problem Solvability

This section maps every Excel-relevant problem documented in [EXCEL_USAGE_REVIEW.md](./EXCEL_USAGE_REVIEW.md) and [PROBLEM_CATEGORIES.md](./PROBLEM_CATEGORIES.md) against each MCP. The goal: for any one problem in our prod fleet, identify which MCPs solve it and which don't.

#### 4.1 Excel-relevant problem inventory

Pulled from [EXCEL_USAGE_REVIEW.md](./EXCEL_USAGE_REVIEW.md) and the A-G categories in [PROBLEM_CATEGORIES.md](./PROBLEM_CATEGORIES.md). Filtered to xlsx-touching issues; cross-cutting ones (Codex paths, PDF, image bloat, base64) excluded unless they directly affect Excel chats.

| ID | Problem | Categories | Prod evidence |
|---|---|---|---|
| **P1** | N+1 same-file reads — same xlsx read 10-200×+ in one chat | B1, B2 | `ef6c1e26` 201× `vcs_seed.xlsx`. Max 360 xlsx tool calls in one chat. 17 chats with ≥10 xlsx tool calls. |
| **P2** | N+1 single-cell writes — `edit_block` per cell instead of batched | B5 | `ef6c1e26` 139 single-cell `edit_block`s. `27214729` 287. |
| **P3** | Verbose xlsx output — null runs, ISO dates, `[To MODIFY cells…]` boilerplate | A4 | `cfbfd7a2` 141 kB single read; ~30% null run bytes; boilerplate ×22. |
| **P4** | Multi-sheet offload bypass — PR #242 only checks `content[0].text` | C1, C4 | 5-sheet xlsx × 150 kB each → first sheet under 200 kB pre-filter; total >700 kB persists. |
| **P5** | Model-swap re-probe — same xlsx re-read after each model swap | D5 | `cfbfd7a2` ran on 9 distinct models; `vcs_seed.xlsx` re-read 9× across swaps. |
| **P6** | Python-literal antipattern — `start_process` python with hardcoded rows; script echoed twice | A3 | `e2b70ff2` 22.8 kB single message; 11 kB script body persisted twice per turn. |
| **P7** | High input tokens (≥1M per chat) — history bloat hits gemini ~1M ceiling | D1, D2 | 524 / 1 753 Excel users own a chat ≥ 1M input tokens (29.9 %). |
| **P8** | Zero-output runaway turns — input ≥500k, output = 0 | D2 | 9 Excel users; 12 chats. 8 users hit single turn ≥800k input. |
| **P9** | No reversibility primitive — abridged/cached results are one-way | D6 | Foundation for safe compaction. Task 26 motivation. |
| **P10** | Multi-table-per-sheet detection missing — model probes per sheet | (cross-cuts B1, A4) | Real spreadsheets have multiple tables per sheet; model can't disambiguate. |
| **P11** | No persistent / cross-chat cache | (B1, D5 indirectly) | Task 08 design goal. Survives Electron restart. |
| **P12** | Schema-first response shape missing — model gets bytes before schema | (cross-cuts A4, B1) | Drives `read_file(xlsx)` antipattern. |
| **P13** | Write fidelity — formulas / formats / charts / named ranges preserved on edit | (write-side) | If write is lossy, model can't safely edit user financial models. |
| **P14** | Soft-deprecation routing of `read_file(xlsx)` | (Task 29) | Without nudging, models keep reaching for `read_file` even when better tools exist. |
| **P15** | Untracked usage capture (gpt-5.4/medium, GLM, Codex) | F1 | 36% of Excel-chat messages have NULL usage. Real cost ~$9-15k vs $3k tracked. |

#### 4.2 Solvability matrix

Symbols: ✅ solves · ⚠ partial / mitigates · ❌ doesn't solve · n/a not applicable. Rows are problems P1-P15; columns are the 10 most relevant MCPs ordered by overall fit.

| | PSU3D0 | MotherDuck | marekrost | jwadow | jdatamunch | ks-xlsx-parser | negokaz | haris-musa | sbroenne | In-house (24/28/29) |
|---|---|---|---|---|---|---|---|---|---|---|
| **P1** N+1 reads | ✅ sessions | ⚠ DuckDB process cache | ❌ reload per call | ✅ FileCache LRU | ✅ persistent index | ⚠ xxhash dedup | ❌ | ❌ | ⚠ COM session | ⚠ Task 08 (per-call, wrong level) |
| **P2** N+1 writes | ✅ transform.write_matrix | ❌ COPY TO lossy | ⚠ SQL UPDATE batched | n/a | n/a | n/a | ⚠ excel_write_to_sheet | ⚠ write_data_to_excel | ✅ COM bulk ops | ✅ xls_write batched |
| **P3** Verbose output | ✅ token_dense default + 64 kB cap | ✅ 1024 rows / 50k chars | ✅ describe-first + SQL aggregates | ✅ atomic ops + 500-row cap | ✅ 8000-token budget | ✅ token-counted chunks | ⚠ 5k cells page | ❌ ANTIPATTERN (per-cell JSON) | ❌ raw COM data | ✅ Task 07 + Task 28 |
| **P4** Multi-sheet bypass | ✅ scoped reads | ✅ scoped SQL | ✅ scoped SQL | ✅ filtered ops | ✅ schema-first | ✅ chunked | ⚠ pagination | ❌ | ❌ | ✅ Task 01 |
| **P5** Model-swap re-probe | ✅ session model-agnostic | ❌ per-process | ❌ | ❌ per-process | ⚠ persistent index survives | ⚠ content-hash dedup | ❌ | ❌ | ❌ | ⚠ Task 17 warns; Task 08 partial |
| **P6** Python-literal | ✅ structured writes; no shell | ⚠ SQL works but lossy save | ⚠ SQL writes back via openpyxl | n/a | n/a | n/a | ⚠ structured writes | ⚠ has apply_formula | ✅ COM bulk write | ✅ xls_write + Task 06 |
| **P7** High input tokens (≥1M) | ✅ compact reads + sessions | ✅ SQL aggregates | ✅ describe_table + SQL | ✅ atomic operations | ✅ token-budget enforcement | ✅ bounded chunks | ⚠ pagination | ❌ | ❌ | ✅ Tasks 07/08/27/28 |
| **P8** Zero-output runaway | ⚠ caps prevent runaway reads | ⚠ row cap + char cap | ⚠ scoped SQL | ⚠ 500-row cap | ✅ token budget + anti-loop | ⚠ chunk caps | ⚠ paging cap | ❌ | ❌ | ⚠ Task 20 (Tier C) |
| **P9** Reversibility | ✅ event-sourced fork/undo/redo | ❌ | ❌ | ❌ | ⚠ index = source of truth | ⚠ citation URIs | ❌ | ❌ | ❌ Excel undo not exposed | ⚠ Task 26 fetch_raw |
| **P10** Multi-table-per-sheet | ✅ shipped + tested | ❌ | ❌ sheet=table | ❌ | ❌ | ⚠ ListObjects only | ❌ | ❌ | ❌ | ⚠ Task 24 (port from PSU3D0) |
| **P11** Persistent / cross-chat cache | ⚠ session export | ⚠ if `--db-path` is file | ❌ | ❌ per-process | ✅ persistent SQLite | ⚠ xxhash content addressing | ❌ | ❌ | ⚠ per-COM-process | ✅ Task 08 SQLite-backed |
| **P12** Schema-first defaults | ✅ `read overview` | ⚠ generic list_tables | ✅ describe_table | ✅ inspect_file | ✅ describe_dataset (best in field) | ✅ chunk schema | ⚠ excel_describe_sheets | ⚠ get_workbook_metadata | ❌ | ✅ xls_describe |
| **P13** Write fidelity | ✅ in-place via umya-spreadsheet | ❌ COPY TO lossy (catastrophic) | ⚠ openpyxl loses charts | n/a | n/a | n/a | ⚠ excelize OK | ⚠ openpyxl issues | ✅ Excel native | ✅ exceljs |
| **P14** Soft-deprecation routing | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ✅ Task 29 |
| **P15** Untracked usage | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ⚠ tokens_saved telemetry pattern (different problem) | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ❌ orthogonal | ✅ Task 03 |

**How to read this:** P1-P10 are the user-facing problems any MCP could plausibly help with. P11-P13 are architectural concerns. P14-P15 are DC-specific layers no external MCP can solve (they live in our integration code).

#### 4.3 PSU3D0 — full problem walk

The most complete external solution. Solves or partially solves **11 of 15 problems**.

| Problem | How PSU3D0 handles it |
|---|---|
| **P1** N+1 reads | ✅ Sessions cache the entire workbook in memory after first parse. All subsequent reads against any range/sheet hit the cached state. The `ef6c1e26` 201-read pattern collapses to **1 file parse + 201 in-memory lookups + 1 batched write**. |
| **P2** N+1 writes | ✅ `transform.write_matrix` accepts a 2D rows array; one tool call writes 100+ cells. `session op` event-sourcing lets the model stage many ops, apply atomically. 139 writes → 1 call. |
| **P3** Verbose output | ✅ Server-level `output_profile=token_dense` flips defaults across ALL tools. `read_table` → CSV. `range_values` → raw arrays. `sheet_page` → compact, no formulas/styles unless asked. Hard caps: 64 kB / 10k cells / 500 items. |
| **P4** Multi-sheet bypass | ✅ Reads are always scoped to a specific sheet+range. The "first content[]" heuristic is irrelevant because PSU3D0 paginates per request. |
| **P5** Model-swap re-probe | ✅ Sessions belong to the chat (workspace + session_id), not the model. New model attaches and reads the cached state — no re-probe. |
| **P6** Python-literal | ✅ Structured tools (`transform.write_matrix`, `write append`, `write clone-template-row`) make `start_process` python unnecessary. The `e2b70ff2` antipattern doesn't arise. |
| **P7** High input tokens | ✅ Compact reads + region-first design + 64 kB cap keep per-turn input bounded. Less direct than SQL aggregates but bounded. |
| **P8** Zero-output runaway | ⚠ The hard byte/cell caps prevent the worst runaway (model can't accidentally request 1M cells), but no pre-flight context-budget guardrail like Task 20. Mitigates, doesn't eliminate. |
| **P9** Reversibility | ✅ Event-sourced session log — fork, checkout, undo, redo, materialize, export. Strictly better than per-result `fetch_raw`. The model can "branch" before risky edits. |
| **P10** Multi-table-per-sheet | ✅ `read overview` returns regions with `bounds`, `header_row`, `region_kind`, `confidence`. Vertical + horizontal gutter splitting. Tested against synthetic fixtures. |
| **P11** Persistent cache | ⚠ Session export/import for cross-process; no native cross-chat awareness. Orchestration on DC's side. |
| **P12** Schema-first defaults | ✅ `read overview` is the canonical first call. Region-aware structural overview before any cell reads. |
| **P13** Write fidelity | ✅ In-place edits via umya-spreadsheet preserve formulas, formats, charts, named ranges in cells outside the change set. |
| **P14** Soft-deprecation routing | ❌ Lives outside MCP scope (DC-specific). |
| **P15** Untracked usage | ❌ Orthogonal — F1 is a DC backend issue. |

**Net:** PSU3D0 is the architectural superset on read+write semantics. Its blind spots are SQL analytical queries (no engine), DC-layer concerns (P14, P15), and the runaway guardrail (P8 partial only).

#### 4.4 MotherDuck MCP — full problem walk

The official DuckDB MCP. Solves or partially solves **6-7 of 15 problems**, but a different subset than PSU3D0.

| Problem | How MotherDuck handles it |
|---|---|
| **P1** N+1 reads | ⚠ DuckDB's columnar parse is cached in-process after first `read_xlsx` call, but each MCP tool roundtrip still costs tokens. 130 SQL queries for 130 rows = 130 calls. **Doesn't fix the antipattern; relies on the model writing one aggregating query instead of 130.** |
| **P2** N+1 writes | ❌ Writes are SQL `INSERT/UPDATE/DELETE` against a registered DuckDB view. Persisting back to xlsx requires `COPY TO` which **strips formulas, formats, charts, comments, named ranges**. Catastrophic for editing user files. |
| **P3** Verbose output | ✅ SQL returns only the rows the model asked for. `SELECT MAX(expense) FROM ...` returns 1 number. Default caps: 1024 rows / 50 000 chars. The 141 kB problem evaporates. |
| **P4** Multi-sheet bypass | ✅ SQL scopes to `read_xlsx(path, sheet => 'X', range => 'Y')`. The model never reads a whole workbook by accident. |
| **P5** Model-swap re-probe | ❌ Connection state is per-server-process. New model gets fresh state unless `--db-path` is a persisted file. No chat-id awareness. |
| **P6** Python-literal | ⚠ SQL writes are an alternative to python-literal (model writes `INSERT INTO sheet VALUES (...)`), but the result is a fresh-written xlsx (lossy fidelity). For "convert PDF to Excel" the model would still typically reach for python because xlsx-write fidelity matters. |
| **P7** High input tokens | ✅ Aggregations / filters / joins are deterministic and return small results. Best fit for "highest expense / median revenue / top 5 vendors" patterns. |
| **P8** Zero-output runaway | ⚠ 1024-row + 50 000-char caps help. No turn-level pre-flight estimate. |
| **P9** Reversibility | ❌ No undo / no fork / no event log. Once `INSERT INTO sheet` runs, it's done. |
| **P10** Multi-table-per-sheet | ❌ `read_xlsx` reads from `A1` to last non-empty cell — mashes multiple tables together silently. **Critical blind spot.** |
| **P11** Persistent cache | ⚠ If `--db-path` is a file, schema persists across restarts. xlsx parses still re-run on each session. |
| **P12** Schema-first defaults | ⚠ `list_tables` + `list_columns` give schema, but they're generic SQL meta — not Excel-aware. No region detection, no named ranges. |
| **P13** Write fidelity | ❌ **Catastrophic.** `COPY TO` produces a fresh xlsx. Strips formulas, formatting, charts, comments, conditional formats, named ranges, defined data validations. Cannot safely edit user's existing financial models. |
| **P14** Soft-deprecation routing | ❌ Lives outside MotherDuck. |
| **P15** Untracked usage | ❌ Orthogonal. |

**Net:** MotherDuck is the analytical Q&A specialist. Solves Problems #2-#3 (the verbose-output / token-bloat axis) better than anything else. Doesn't help with N+1, model-swap, multi-table, write fidelity, or reversibility. **Use it for read-only analytics; don't use it to edit financial models.**

#### 4.5 The other ~13 MCPs — quick-fire scorecards

For each remaining MCP, what subset of Excel problems they actually move the needle on. License blockers and quality issues called out.

##### 4.5.1 Strong / niche (worth borrowing ideas from)

**marekrost/mcp-server-spreadsheet** (MIT, Python, DuckDB) — solves **P3, P4, P7, P12** via DuckDB SQL. Closest match to our Task 28 design. Multi-format (xlsx + csv + ods). `describe_table` is a strong schema-first contract. **Misses P1, P5, P10**: no caching (loads workbook every call), no chat-id awareness, sheet=table only. **Highly forkable** — ~750 LOC single file, MIT.

**jwadow/mcp-excel** (AGPL-3.0 ⚠, Python) — solves **P1, P3, P7, P12** via the explicit FileCache (LRU 5/1GB/10min, mtime-keyed) + atomic operations that return numbers/formulas not rows + 4-signal HeaderDetector + 500-row hard cap. **AGPL is a hard adoption blocker** for closed-source DC; algorithms can be re-implemented under MIT but no code copy.

**jgravelle/jdatamunch-mcp** (dual-licensed: free non-commercial / paid commercial ⚠, Python) — solves **P3, P7, P8, P11** via persistent SQLite indexes at `~/.data-index/` with HEAD-SHA invalidation, token-budget enforcement (default 8000), anti-loop detection, wide-table auto-pagination at 60 cols, per-call `tokens_saved` telemetry. **Best architectural reference for token-cost telemetry** but commercial use restricted; lift the patterns, not the code.

**knowledgestack/ks-xlsx-parser** (MIT, Python lib) — solves **P3, P12** via token-counted RAG chunks with citation URIs (`file.xlsx#Sheet!A1:F18`). The citation-URI shape is the response design we want for `read_file` chunks. xxhash content addressing helps with P11 partially. Read-only.

##### 4.5.2 Pagination-only / generic (basic mitigation)

**negokaz/excel-mcp-server** (MIT, Go, 942 stars) — solves **P3, P4** via `EXCEL_MCP_PAGING_CELLS_LIMIT=5000` + nextRange pointer. Returns HTML tables. excelize backend has better write fidelity than openpyxl. **Misses everything else** — no schema-first, no SQL, no caching, no multi-table.

**ArchimedesCrypto/excel-reader-mcp** (MIT, Node.js) — solves **P3** via auto-chunking at 100 KB with `nextChunk` hint. Read-only. Single tool. Otherwise basic.

**ZephyrDeng/spreadsheet-mcp** (MIT, TypeScript) — solves **P3** trivially (returns 2D arrays as JSON, compact-ish). No SQL, no caching, no schema-first. Demo-grade.

##### 4.5.3 COM / Excel-native (Windows-only)

**sbroenne/mcp-server-excel** (MIT, C#, 149 stars) — solves **P2, P6, P13** via Excel COM API (perfect write fidelity, native bulk ops, Power Query, DAX, VBA). **Windows-only**, requires Excel installed. Out of scope for DC's cross-platform Electron deployment but architecturally the strongest write fidelity in the field. Notable for marketing "64 % fewer tokens" with their CLI variant — claims MCP schema bloat itself is a token cost. Worth investigating if we ever pursue Windows-specific paths.

##### 4.5.4 Antipattern / not-helpful

**haris-musa/excel-mcp-server** (MIT, Python, 3 789 stars) — **antipattern** for Problem #3. `read_data_from_excel` returns full pretty-printed JSON of every cell with `address`/`value`/`row`/`column`/validation per cell. No cap, no schema-first, no caching. Despite being the most-installed Excel MCP, **its response shape is approximately the bytes-bloat we're solving**. Useful as proof that "lots of stars" ≠ "good for our use case."

**jonemo/openpyxl-mcp-server** (MIT, Python, 19 stars) — thin 356-line wrapper. Cell-by-cell verbose dumps. Doesn't solve anything we care about.

**yzfly/mcp-excel-server** (no license) — pandas-based. **No license file** — cannot adopt or borrow code; discount entirely.

**guillehr2/Excel-MCP-Server-Master** (MIT, Python) — generic openpyxl wrapper. No notable design choices.

**mort-lab/excel-mcp** (MIT, Python) — 20 tools, Pydantic. Generic openpyxl. Same fidelity issues.

##### 4.5.5 Out of scope

**xing5/mcp-google-sheets** (MIT) — Google Sheets cloud only. Not relevant for local xlsx.

**chrisryugj/kordoc** (MIT, Node.js, 896 stars) — Korean government docs (HWP/HWPX/PDF/XLSX/DOCX) → Markdown. Strong on tables in scanned PDFs and HWP. Basic XLSX support. The Markdown-first response shape is a useful reference.

#### 4.6 Problems no MCP fully solves

Some problems are inherently DC-layer concerns and no external MCP can address them. Listing for clarity:

| Problem | Why no MCP solves |
|---|---|
| **P5** Model-swap re-probe (cross-chat) | Requires chat-id awareness. No MCP has chat-id semantics. PSU3D0 sessions are the closest but live per-MCP-process, not per-DC-chat. |
| **P11** Persistent cross-chat cache | Same — chat-id awareness needed. jdatamunch's persistent SQLite index is the closest pattern but doesn't survive across users. |
| **P14** Soft-deprecation routing of `read_file(xlsx)` | Lives in DC's tool-result interceptor. No external MCP can hint about another tool. |
| **P15** Untracked usage capture | DC backend / provider adapter concern. Not an MCP issue. |

#### 4.7 What every external MCP demonstrates we should add

Across the 15-MCP review, these features appear repeatedly enough to be considered **best-practice for any Excel MCP**:

1. **Schema-first response shape** — `describe_table` (marekrost), `inspect_file` (jwadow), `describe_dataset` (jdatamunch), `read overview` (PSU3D0). Every well-designed MCP leads with schema. Antipattern (haris-musa) leads with bytes.
2. **Hard response caps** — 500 rows (jwadow), 1024 rows (MotherDuck), 5000 cells (negokaz), 64 kB (PSU3D0), 8000 tokens (jdatamunch). Without a cap, you eventually ship a 141 kB read.
3. **mtime-keyed cache invalidation** — jwadow, jdatamunch, PSU3D0 sessions. **Must be in our Task 08 cache key.**
4. **Citation URIs** — `file.xlsx#Sheet!A1:F18` (ks-xlsx-parser). Every read response should carry a `source_range` so the model can cite/recover.
5. **Anti-loop / token-budget telemetry** — jdatamunch warns when an agent paginates row-by-row. Per-call `tokens_saved` reporting validates the project to stakeholders post-launch.
6. **Region-aware overview before any cell reads** — PSU3D0's `read overview`. Single most important read-design lesson.
7. **Workbook-level cache** (sessions) — PSU3D0. Strictly better than per-call cache for the actual `ef6c1e26` antipattern.
8. **Server-level token-dense default profile** — PSU3D0's `output_profile=token_dense`. Single switch, applies everywhere; cleaner than per-tool flags.

These are listed in the bottom-line recommendation in Section 5 and the action items in [EXCEL_MCP_REVIEW.md](./EXCEL_MCP_REVIEW.md#9-action-items-if-architecture-c-is-selected).

### 5. Bottom-Line Recommendation

**Build our own (Tasks 24, 28, 29 as designed), but vendor and adapt three open-source pieces to skip plumbing work:**

1. **Fork `marekrost/mcp-server-spreadsheet`'s DuckDB engine** as the core of Task 28. ~750 lines of MIT-licensed Python. Replace `_sheet_to_records` with multi-region-aware extraction (calling our Task 24 region detector first), add Task 08 cache in front of `load_workbook`, and we have `xls_query` in days, not weeks. Their type inference, header dedup, atomic save, and `_extract_target_table` mutation parser are all directly reusable. Reach out to the maintainer to confirm intent — solo MIT project, very forkable.

2. **Re-implement `jwadow/mcp-excel`'s `HeaderDetector` algorithm** under MIT inside our exceljs path for Task 24. Don't copy code (AGPL); copy the four-signal weighting (fill rate 20%, uniqueness, string ratio, following-row consistency variance). Cite the algorithm in comments.

3. **Re-implement `PSU3D0/spreadsheet-mcp`'s region-detection response shape** — `regions: [{bounds, header_row, region_kind}]` — as the canonical Task 24 output. The contract is well-designed; the actual gutter algorithm is straightforward to write fresh against exceljs.

**Add three features we hadn't thought of:**

- Per-call `tokens_saved` telemetry (jdatamunch pattern) — drops straight into our PostHog tracking and gives Dmitry a hard number to point at.
- Citation URI on every read response (`file.xlsx#Sheet!A1:F18`, ks-xlsx-parser pattern) — pairs perfectly with `fetch_raw` reversibility (Task 26) for trust and debuggability.
- Mtime in cache key (jwadow pattern) — must be in Task 08 cache key to avoid stale results.

**Why not just adopt PSU3D0 wholesale?** Three reasons: (a) Rust binary distribution conflicts with our Electron + Node.js codebase, requiring us to ship a platform-specific binary per OS; (b) the session/fork model is heavyweight overhead for our three-tool target; (c) we control the semantics by building it ourselves and can wire it into the existing soft-deprecation of `read_file(xlsx)` in Task 29 cleanly. PSU3D0 remains the best architectural reference and we should keep linking to its README and tests in our own design docs.

**Why not adopt marekrost wholesale?** (a) No multi-table-per-sheet (the very thing Task 24 exists to solve), (b) no caching, (c) we want exceljs not openpyxl (Node-native, no Python runtime in Electron app). Forking the SQL plumbing only makes more sense than running their server alongside ours.

**Net assessment:** Tasks 24/28/29 remain the right scope. We can ship them ~30% faster by lifting the marekrost SQL plumbing and the jwadow header heuristic. Borrow the response-shape ideas from PSU3D0, the telemetry ideas from jdatamunch, and the citation-URI idea from ks-xlsx-parser. **No project in the field combines exceljs + DuckDB + multi-table detection + per-chat cache + reversibility — that combination is genuinely novel and worth building.**

### 6. Summary

A condensed view of the entire investigation. Use this as the briefing slide.

#### 6.1 Coverage of EXCEL_USAGE_REVIEW.md problems

| Problem | Best external MCP | Coverage | Gap from external = work for us |
|---|---|---|---|
| **P1** N+1 reads | PSU3D0 (sessions) | ✅ workbook-level cache | Adopt PSU3D0's session model in our cache layer (rework Task 08). |
| **P2** N+1 writes | PSU3D0, sbroenne, in-house | ✅ batched-write tools shipped | Implement `xls_write({changes:[…]})` (Task 24). |
| **P3** Verbose output | MotherDuck (SQL aggregates) + PSU3D0 (token_dense) | ✅ both approaches work | Tasks 07 + 28 + adopt server-level token_dense profile. |
| **P4** Multi-sheet bypass | All scoped-read MCPs | ✅ scoping fixes it | Task 01 (sum content[]) for legacy `read_file` path. |
| **P5** Model-swap re-probe | PSU3D0 sessions | ✅ via session model | Adopt session model; Task 17 mid-chat warning. |
| **P6** Python-literal | PSU3D0, in-house | ✅ structured writes eliminate temptation | Tasks 24 + 06. |
| **P7** High input tokens | MotherDuck (SQL) + PSU3D0 (compact) | ✅ both | Tasks 28 + 27 + 08. |
| **P8** Zero-output runaway | jdatamunch (token budget + anti-loop) | ⚠ partial | Task 20 pre-flight context guardrail (Tier C). |
| **P9** Reversibility | PSU3D0 (event-sourced sessions) | ⚠ external better than ours | Evolve Task 26 toward session log post-P1. |
| **P10** Multi-table-per-sheet | PSU3D0 (only one) | ✅ algorithm + tests shipped | Port to TypeScript/exceljs (Task 24). |
| **P11** Persistent cross-chat cache | jdatamunch (SQLite index pattern) | ⚠ external lacks chat-id awareness | Task 08 SQLite-backed; uniquely DC's design. |
| **P12** Schema-first defaults | jdatamunch / PSU3D0 / marekrost | ✅ pattern proven | Task 24 `xls_describe`. |
| **P13** Write fidelity | PSU3D0 (umya), sbroenne (COM) | ✅ in-place edits | exceljs in Task 24. |
| **P14** Soft-deprecation routing | (none — DC-layer) | ❌ orthogonal to MCPs | Task 29. |
| **P15** Untracked usage | (none — DC-backend) | ❌ orthogonal | Task 03. |

**Tally for our prod problems:** 13 of 15 problems are addressable by combining 2-3 external MCP designs. Only P14 and P15 are pure DC concerns no external MCP can touch.

#### 6.2 Per-MCP fitness ranking against our specific problems

Based on Section 4.2 matrix (✅ = 2 points, ⚠ = 1 point, ❌ = 0). Out of 15 problems × 2 = 30 max. Higher is better.

| Rank | MCP | Score | Notes |
|---|---|---|---|
| 1 | **In-house (Tasks 24/28/29)** | 24-26 | Targeted to our exact problems; only one solving P14 + P15. |
| 2 | **PSU3D0** | 22 | Architectural superset; gaps are SQL (P7 partial only via compact reads) and DC-layer concerns. |
| 3 | **MotherDuck MCP** | 11-12 | Excellent on analytical Q&A axis (P3, P4, P7); fails on P1, P2, P5, P9, P10, P13. |
| 4 | **marekrost** | 10-11 | Closest to our Task 28 SQL design; misses P1, P5, P10. |
| 5 | **jwadow** | 11-12 | Strong on cache + atomic ops; AGPL blocker; no writes. |
| 6 | **jdatamunch** | 12-13 | Best architectural reference; commercial license blocker; no writes. |
| 7 | **knowledgestack/ks-xlsx-parser** | 7-8 | Citation URI pattern is the gem. |
| 8 | **negokaz** | 5-6 | Pagination only. |
| 9 | **sbroenne** | 6-7 | Best fidelity; Windows-only. |
| 10 | **haris-musa** | 1-2 | Antipattern despite popularity. |
| 11-15 | jonemo, ZephyrDeng, mort-lab, guillehr2, yzfly | 0-2 | Demo-grade or no license. |

#### 6.3 Where the design lessons compound

If Architecture C (hybrid in-house) is adopted (see [EXCEL_MCP_REVIEW.md §6](./EXCEL_MCP_REVIEW.md#8-recommendation)), the synthesis from this research is:

**From PSU3D0:**
- Workbook-level session cache (rework Task 08).
- Region-detection algorithm + response contract (Task 24).
- `output_profile=token_dense` server-level switch (replaces per-tool flags).
- Event-sourced session log as future evolution of Task 26.
- Skill prompt patterns (`EXPLORE_SKILL.md`, `SAFE_EDITING_SKILL.md`).

**From MotherDuck MCP / DuckDB:**
- SQL surface as the analytical Q&A interface (Task 28).
- 1024-row + 50 000-char default caps.
- Read-only by default; write opt-in.
- `.mcpb` packaging shape as a precedent.

**From jdatamunch:**
- `tokens_saved` per-call telemetry → directly into PostHog tracking.
- Anti-loop detection (warn when paginating row-by-row).
- Token-budget enforcement.

**From jwadow:**
- 4-signal HeaderDetector algorithm (re-implement under MIT).
- mtime-keyed cache invalidation (must be in Task 08 cache key).

**From ks-xlsx-parser:**
- Citation URIs (`file.xlsx#Sheet!A1:F18`) on every read response.

**From marekrost:**
- DuckDB type inference + header dedup + atomic save (~750 LOC of MIT plumbing to fork).

**From negokaz:**
- HTML-table response option for visual-diff use cases (worth A/B testing).

**From sbroenne:**
- "MCP schema bloat is a token cost" insight — review our own MCP tool schemas for verbosity.

#### 6.4 Final decision

**Build in-house (Tasks 24/28/29) using Architecture C** — this combines the best lessons from PSU3D0 (session model, region detection, token_dense profile), MotherDuck/DuckDB (SQL analytical Q&A), jdatamunch (telemetry), and jwadow (cache invalidation rules). All ideas are open-source compatible (MIT or Apache-2.0); algorithms re-implemented where source is AGPL.

**Do not adopt any single external MCP wholesale** because:
- PSU3D0 lacks SQL and has Rust binary distribution friction.
- MotherDuck has catastrophic write fidelity (`COPY TO` strips formulas / formats / charts).
- jwadow is AGPL-3.0 and read-only.
- jdatamunch is commercially licensed and read-only.
- All other 11 reviewed MCPs are either antipatterns or demo-grade.

**Concrete next-step actions** (sourced from this review):

1. Rework [Task 08](./tasks/08-per-chat-tool-result-cache.md) from per-call cache to workbook-level session cache (PSU3D0 lesson).
2. Adopt 1024-row / 50 000-char defaults in [Task 28](./tasks/28-xls-query-duckdb.md) (MotherDuck).
3. Add `output_profile=token_dense` server-level config (PSU3D0).
4. Add `tokens_saved` telemetry to every effectiveness-task tool response (jdatamunch).
5. Add `source_range` citation URI to every xlsx read response (ks-xlsx-parser).
6. Port PSU3D0's region-detection algorithm to TypeScript/exceljs in [Task 24](./tasks/24-xls-first-class-tools.md).
7. Re-implement jwadow's 4-signal HeaderDetector under MIT.
8. Plan a future Task 30 — event-sourced session ops + `analyze ref-impact` preflight (PSU3D0 reversibility lessons).

#### 6.5 Cross-references

- [EXCEL_USAGE_REVIEW.md](./EXCEL_USAGE_REVIEW.md) — fleet-wide problem evidence + prioritized fix plan.
- [EXCEL_MCP_REVIEW.md](./EXCEL_MCP_REVIEW.md) — deep-dive 3-way comparison (PSU3D0 vs MotherDuck vs in-house) with architecture options A-D.
- [SUMMARY.md](./SUMMARY.md) — fleet-wide effectiveness investigation.
- [PROBLEM_CATEGORIES.md](./PROBLEM_CATEGORIES.md) — A-G category index.


---

# Part II — Architecture Review


## Excel MCP Review — DuckDB-based, Native, In-house

Detailed comparison of the three architectural choices for solving the Excel token-consumption problems documented in [EXCEL_USAGE_REVIEW.md](./EXCEL_USAGE_REVIEW.md):

1. **MotherDuck MCP** (`motherduckdb/mcp-server-motherduck`) — generic DuckDB SQL MCP, no Excel-specific surface but uses DuckDB's native `read_xlsx`.
2. **PSU3D0** (`PSU3D0/spreadsheet-mcp`) — Rust, sessions + region detection + reversibility, no SQL.
3. **Our in-house plan** (Tasks 24/28/29) — exceljs (writes / describe) + DuckDB native (SQL) + multi-table detection + per-chat cache + soft-deprecation hint.

This review is intentionally DuckDB-aware, unlike the broader [EXCEL_MCPS_RESEARCH.md](./EXCEL_MCPS_RESEARCH.md) landscape report.

### TL;DR

- **MotherDuck MCP** is a generic DuckDB SQL surface (5 tools), already shipping as a `.mcpb` bundle, with the **lowest engineering cost** to ship Excel SQL Q&A. **Doesn't solve Problem #1 (N+1 reads), Problem #3 (model-swap re-probe), or any write workflow** — it's just a SQL terminal pointed at xlsx.
- **PSU3D0** has the **best architectural answer to Problem #1**: workbook-level sessions = automatic in-memory cache for *all* reads regardless of range. Plus region detection, reversibility (undo/redo/fork), and dry-run preflight. **No SQL** — analytical Q&A degrades to model-side compute.
- **Our in-house plan** is the only one that combines **SQL + structured writes + multi-table detection + soft-deprecation routing**. Highest engineering cost (~3-4 weeks). Open question: should we adopt PSU3D0's session model in place of Task 08's per-call cache?
- **Recommended path:** **Architecture C (hybrid)** — adopt the **session model from PSU3D0** (workbook-level cache) and **SQL from MotherDuck/DuckDB** (analytical Q&A), build the integration ourselves. Skip the binary distribution headache; skip the "no SQL" coverage gap.

### 1. The three candidates

#### 1.1 MotherDuck MCP (`motherduckdb/mcp-server-motherduck`)

**Repository:** https://github.com/motherduckdb/mcp-server-motherduck
**License:** MIT · **Language:** Python · **Stars:** 476 · **Last push:** 2026-04-29 · **Active:** ✅
**Distribution:** `uvx mcp-server-motherduck` · PyPI · `.mcpb` release artifact · Docker-friendly
**Framework:** FastMCP (modern Python MCP framework)

**Tool surface (5 tools):**

| Tool | Description |
|---|---|
| `execute_query` | Run arbitrary DuckDB SQL — `SELECT * FROM read_xlsx('/path/file.xlsx')` |
| `list_databases` | List attached databases (relevant for MotherDuck cloud, less for xlsx) |
| `list_tables` | List tables and views |
| `list_columns` | List columns of a given table/view |
| `switch_database_connection` | Hot-swap the active connection (gated by `--allow-switch-databases`) |

**Default response caps:** 1024 rows · 50 000 chars · `--query-timeout` configurable.
**Connection modes:** local `.duckdb` file · in-memory · S3 · MotherDuck cloud.
**Excel handling:** **None directly.** The model writes `SELECT * FROM read_xlsx('/path/file.xlsx', sheet => 'Annual', header => true)` — the DuckDB `excel` extension parses xlsx in-process. Same for `.csv`, `.parquet`, `.json`. No xlsx-specific tools, no schema discovery, no writes.
**Reads:** SQL only. No raw cell inspection, no formula introspection, no formatting access.
**Writes:** SQL only — `INSERT / UPDATE / DELETE` against a registered DuckDB table works fine, but writing back to xlsx requires `COPY (SELECT …) TO 'file.xlsx'` which **doesn't preserve formulas, formatting, charts, comments, conditional formats, or named ranges.** It's a fresh-write, lossy.

**MCPB readiness:** Ships an `.mcpb` bundle directly from GitHub releases. Drop-in for any MCPB-aware host (Claude Desktop, etc.). Five releases tagged with the bundle attached.

#### 1.2 PSU3D0 (`PSU3D0/spreadsheet-mcp`)

**Repository:** https://github.com/PSU3D0/spreadsheet-mcp
**License:** Apache-2.0 · **Language:** Rust · **Stars:** 44 · **Last push:** 2026-04-01 · **Active:** ⚠ slowing
**Distribution:** prebuilt native binaries (Linux x64, macOS arm64/x64, Windows x64) · Cargo · Docker (`ghcr.io/psu3d0/spreadsheet-mcp:latest|full`) · npm `agent-spreadsheet` (CLI launcher) · WASM target in source (experimental, not packaged)

**Tool surface (~50 tools across 6 groups):**

| Group | Representative tools |
|---|---|
| `read` | `sheets`, `overview`, `values`, `cells`, `page`, `table`, `names`, `workbook`, `layout`, `export` |
| `write` | `cells`, `import`, `append`, `clone-template-row`, `clone-row-band`, `formulas-replace`, `name-define/update/delete`, `transform-batch`, `style-batch`, `formula-pattern`, `structure-batch` |
| `analyze` | `find-value`, `formula-trace`, `find-formula`, `scan-volatiles`, `ref-impact`, `formula-map` |
| `verify` | `proof`, `diff` |
| `session` | `start`, `op`, `apply`, `log`, `undo`, `redo`, `fork`, `checkout`, `materialize`, `export`, `import` |
| `workbook` | `copy`, `recalculate`, `describe`, `list` |

**Token-efficiency design (from `docs/tool-output-verbosity-proposal.md`):**

- Server-level **`output_profile=token_dense`** as the default for ALL tools.
- Per-tool defaults: `read_table` → CSV (no type wrappers); `range_values` → raw 2D arrays; `sheet_page` → compact, no formulas/styles unless asked.
- Hard caps: `SPREADSHEET_MCP_MAX_PAYLOAD_BYTES=65536` (64 kB), `MAX_CELLS=10 000`, `MAX_ITEMS=500`.
- Pagination is **opt-in if requested, automatic if exceeded**. `truncated: true` + `next_offset` cursors only when needed.

**Sessions = workbook-level cache:**

```
asp session start --base file.xlsx → session_id
asp read values --session <id> --range C5    ← in-memory cache hit
asp session op --session <id> --ops @writes  ← staged
asp session apply --session <id>
asp session materialize --session <id> --output final.xlsx
```

The workbook is parsed **once** per session. All reads against any range/sheet hit the in-memory state. Writes are event-sourced with full undo/redo/fork lifecycle.

**Region detection (multi-table-per-sheet):** Algorithm documented in `docs/HEURISTICS.md`. Vertical + horizontal gutter splits. Returns `{bounds, header_row, region_kind: Data|Table|Parameters|Calculator|Outputs|Metadata, confidence}`. Tested against synthetic fixtures; honest about limitations (single financial-spreadsheet test corpus, no merged-cell support, English-centric).

**Preflight & verification:** `analyze ref-impact` previews structural changes (shifted spans, broken absolute refs, formula deltas) without mutating. `verify proof` confirms specific target cells changed as expected. `verify diff` shows only direct edits, excluding recalc cascade.

**No SQL.** All analytical Q&A is via `read table` + `find-value` + model-side filter/aggregate.

**MCPB readiness:** Not currently — would require either (a) embedding 4 platform binaries (~120 MB MCPB) with platform-conditional launcher, or (b) shipping the experimental WASM build with partial capability matrix (no SQL, no structure mutations, no replace-in-formulas, no verification, no fork).

#### 1.3 Our in-house plan (Tasks 24/28/29)

**Specs:** [Task 24](./tasks/24-xls-first-class-tools.md) · [Task 28](./tasks/28-xls-query-duckdb.md) · [Task 29](./tasks/29-read-file-xlsx-soft-deprecation.md)
**License:** internal · **Language:** TypeScript / Node.js (matches DC's existing local-server)
**Distribution:** integrated into DC's local Fastify server; no standalone MCP — runs in-process

**Tool surface (4 tools):**

| Tool | Implementation |
|---|---|
| `xls_describe(path)` | exceljs — schema, multi-table detection (gutter algorithm ported from PSU3D0), named ranges, formula presence flags, head samples |
| `xls_query(path, sheet?, range?, sql)` | DuckDB native (`duckdb` npm) — registered view on xlsx, materializes to TABLE for hot keys, ART indexes optional |
| `xls_write(path, changes)` | exceljs — batched cell writes, formulas with cached results, formatting preserved |
| `read_file(*.xlsx*)` (existing, soft-deprecated) | xlsx serializer + deprecation hint pointing at xls_describe / xls_query |

**Supporting infrastructure:**

| Component | Task |
|---|---|
| Per-chat tool-result cache (mtime-keyed, persisted to SQLite) | [Task 08](./tasks/08-per-chat-tool-result-cache.md) |
| `fetch_raw(handle)` reversibility primitive | [Task 26](./tasks/26-fetch-raw-primitive.md) |
| Cache invalidation on writes (`emitPathMutated` event bus) | Cross-task amendment |
| PR #242 offload — sum across `content[]` parts | [Task 01](./tasks/01-offload-sum-all-content-parts.md) |
| Trim verbose xlsx output (null runs, ISO dates, boilerplate) | [Task 07](./tasks/07-trim-verbose-xlsx-output.md) |
| Capture untracked usage (gpt-5.4/medium, GLM, Codex) | [Task 03](./tasks/03-capture-untracked-usage.md) |
| Smarter context optimizer (graduated compaction, dedupe) | [Task 27](./tasks/27-smarter-context-optimizer.md) |

**Engineering effort:** 3-4 weeks across the P0 + P1 task waves (per `EXCEL_USAGE_REVIEW.md` ship plan).

**MCPB readiness:** Already integrated into DC's local-server which is already MCPB-distributed (`desktop-commander.mcpb`, `server.type: "node"`). No separate bundle.

### 2. Mapping to user problems

The three top problems from `EXCEL_USAGE_REVIEW.md` and how each candidate addresses them.

#### Problem #1 — N+1 same-file reads (B1, B2, B5)

**Recap:** `ef6c1e26` read `vcs_seed.xlsx` 201 times + 139 single-cell `edit_block` writes. Skill iterates per row; no cache; every read replays in history.

| Candidate | How it solves Problem #1 |
|---|---|
| **MotherDuck MCP** | ⚠ Partial. The model can write one SQL query that aggregates over the file (`SELECT VC, summary FROM read_xlsx(...)`), then loop in *application logic* per row — but DuckDB doesn't dedupe identical reads across calls. If the model still issues 130 `read_xlsx` calls for 130 rows, all 130 hit the file (DuckDB caches columnar parse results in-process, but the SQL roundtrip still costs tokens per call). **Better with skill discipline; not enforced.** |
| **PSU3D0** | ✅ **Best answer.** Sessions cache the workbook itself. 130 reads against 130 different ranges all hit the in-memory parsed state. 1 file-parse + 130 cheap reads + 1 batched `transform.write_matrix` = ~5 tool calls. **Strictly better than any per-call cache** because it caches at the workbook level, not the (toolName, args) level. |
| **In-house** | ⚠ Partial. Task 08's cache keys on `(toolName, args)` — different ranges = different keys = all misses for the `ef6c1e26` pattern. **Workbook-level cache (PSU3D0's model) would be strictly better.** Task 24's `xls_describe` + `xls_query` + `xls_write` reduces *call count* (described once, queried with SQL, written batched), but doesn't cache as elegantly as sessions. **Open design question: adopt PSU3D0's session model.** |

**Winner for Problem #1:** PSU3D0 (architectural lesson the in-house plan should learn from).

#### Problem #2 — Verbose xlsx output + multi-sheet bypass (A4, C1, C4)

**Recap:** 141 kB single read of `DC Seed Financial Model (10).xlsx`. ~30 % null runs, full ISO dates, `[To MODIFY cells…]` boilerplate ×22. Multi-sheet xlsx bypasses PR #242 offload (1 MB cap on `content[0].text`).

| Candidate | How it solves Problem #2 |
|---|---|
| **MotherDuck MCP** | ✅ Solved. SQL queries return only the rows the model asked for. `SELECT MAX(expense) FROM read_xlsx(...)` returns 1 number, ~30 bytes. No null cells, no ISO date wrappers, no boilerplate. 1024-row default cap + 50 000-char cap protect against runaway. **The 141 kB problem disappears entirely.** |
| **PSU3D0** | ✅ Solved. `output_profile=token_dense` server default + 64 kB byte cap + region-first reads (`asp read overview` returns ~2 kB schema before any cells are read). CSV format default for `read table` (no type wrappers). Multi-sheet bypass becomes irrelevant because reads are scoped to a sheet+range. |
| **In-house** | ✅ Solved via combination: Task 07 trims xlsx (null runs → run-length, ISO dates → short, boilerplate-once); Task 01 fixes multi-sheet `content[]` summing; Task 28's `xls_query` returns SQL rows not full sheets. Less elegant than PSU3D0's single `output_profile` switch — three patches instead of one default. |

**Winner for Problem #2:** Tie between PSU3D0 (most elegant — single switch) and MotherDuck (effective but no schema-first / no Excel-aware response shape). In-house solves it with three patches.

#### Problem #3 — Model-swap re-probe + python-literal antipattern (D5, A3)

**Recap:** `cfbfd7a2` ran 9 distinct models, each re-probed. `e2b70ff2` PDF→Excel: model writes `start_process` python with all rows hardcoded as Python list literals; `start_process` echoes script back twice (22.8 kB single message).

**Model-swap half:**

| Candidate | How it solves the swap re-probe |
|---|---|
| **MotherDuck MCP** | ⚠ Partial. SQL is model-agnostic — same query string returns the same result regardless of which model issues it — but the connection state (attached databases, registered views) is per-server-process. New model gets fresh state unless `--db-path` is a persisted file. **No automatic discovery sharing across models.** |
| **PSU3D0** | ✅ Solved. Sessions are model-agnostic. New model attaches to the same `session_id`, sees the cached workbook + the operation log + previously-discovered regions. No re-probe. |
| **In-house** | ⚠ Partial. Task 08 cache helps if new model issues identical args (rare in practice — models pick different tools). Task 17 just warns the user. **Adopting workbook-level sessions would solve this completely.** |

**Python-literal half:**

| Candidate | How it solves the python-literal antipattern |
|---|---|
| **MotherDuck MCP** | ❌ Not directly. Model can `INSERT INTO sheet VALUES (...)` via SQL, but the result is a fresh-written xlsx (lossy — no formulas/formats preserved). For "convert PDF to Excel", model would still typically reach for `start_process` python because xlsx-write fidelity matters. |
| **PSU3D0** | ✅ Solved. `transform.write_matrix` accepts structured rows JSON. `write append` is table-aware (extends table range, preserves computed-column formulas). `clone-template-row` for "fill row 5 to 100 like row 4". No `start_process` involvement, no script-as-data antipattern. |
| **In-house** | ✅ Solved. `xls_write({changes:[…]})` via exceljs — same shape as PSU3D0's `transform.write_matrix`. exceljs preserves formulas, formatting, charts. Pair with Task 06 (strip `start_process` echo) for the residual antipattern in `e2b70ff2`. |

**Winner for Problem #3:** PSU3D0 (both halves) and in-house (python-literal half via exceljs). MotherDuck lacks fidelity-preserving writes.

### 3. Side-by-side comparison

#### 3.1 Setup & distribution

| | MotherDuck MCP | PSU3D0 | In-house (DuckDB+exceljs) |
|---|---|---|---|
| **Install** | `uvx mcp-server-motherduck` (zero-config) | `npm i -g agent-spreadsheet` (downloads platform binary), `cargo install`, or Docker | Embedded in DC local-server; no install for users |
| **Distribution shape** | PyPI · `.mcpb` bundle · Docker | 4 native binaries · Cargo crate · Docker · npm CLI launcher · WASM (experimental) | DC bundle (`desktop-commander.mcpb`) |
| **MCPB-ready today** | ✅ ships `.mcpb` from releases | ❌ not (binary distribution issue; WASM unpackaged) | ✅ via DC's existing bundle |
| **Platform-agnostic** | ✅ Python on Mac/Linux/Win | ⚠ Native binaries per platform | ✅ via Node + DuckDB-WASM or DuckDB native (npm `duckdb` has prebuilds for major platforms) |
| **Bundle size** | ~50 MB (Python deps + DuckDB binary in `.mcpb`) | ~120 MB if 4 binaries embedded; ~5-8 MB if WASM | ~30 MB (DuckDB native) or ~25 MB (DuckDB-WASM) added to DC bundle |
| **Container option** | Easy (Python image) | Both `:latest` and `:full` images on ghcr.io | n/a (in-process) |
| **Setup complexity for DC users** | Low (uvx) | Low-Medium (npm CLI hides platform pick) | Zero (already inside DC) |
| **Zero-touch upgrade** | Via PyPI / .mcpb release | Via npm `npm update -g agent-spreadsheet` | Via DC auto-updater |

#### 3.2 Tool surface

| | MotherDuck MCP | PSU3D0 | In-house |
|---|---|---|---|
| **Tool count** | 5 | ~50 across 6 groups | 4 (xls_describe, xls_query, xls_write, read_file deprecation hint) |
| **Schema discovery** | `list_tables` + `list_columns` (generic, not Excel-aware) | `read overview`, `read names`, `read sheets`, `read workbook` (Excel-aware, multi-table per sheet) | `xls_describe` (Excel-aware, multi-table per sheet) |
| **SQL** | ✅ full DuckDB SQL | ❌ none | ✅ DuckDB SQL via `xls_query` |
| **Cell-level reads** | via SQL only | `read cells`, `read values`, `read layout`, `read page` | via xls_read (optional, Task 24) |
| **Region detection** | ❌ | ✅ shipped + tested | ⚠ to be built (port from PSU3D0 algorithm) |
| **Named ranges** | ❌ | ✅ read + write (`name define/update/delete`) | ⚠ surfaced in xls_describe; no dedicated mutation |
| **Formula introspection** | ❌ (DuckDB sees evaluated values only) | ✅ `formula-map`, `formula-trace`, `find-formula`, `scan-volatiles` | ⚠ via exceljs in xls_describe; no graph traversal |
| **Cell-level writes** | via SQL `INSERT/UPDATE/DELETE` (lossy) | ✅ `transform.write_matrix`, `cells`, `import` (preserves formats/formulas) | ✅ `xls_write({changes:[…]})` via exceljs |
| **Batched writes** | via SQL bulk insert | ✅ batch-aware tools (`transform-batch`, `structure-batch`, `style-batch`, `formula-pattern`) | ✅ `xls_write({changes:[…]})` |
| **Formula writes** | ✅ via SQL `(formula = '=A1*2')` but lossy on save-to-xlsx | ✅ first-class with parse-policy diagnostics | ✅ via exceljs (`{formula, result}` pattern) |
| **Style / format writes** | ❌ | ✅ `style-batch`, `style-patch`, ARGB normalization, font/fill/border | ⚠ via exceljs format strings |
| **Chart / pivot writes** | ❌ | ⚠ partial via `style-batch` | ❌ exceljs has limited chart support |
| **Append-to-table** | ❌ (would rewrite file) | ✅ `write append` (table-aware footer detection) | ⚠ via xls_write but not table-aware |
| **Template row cloning** | ❌ | ✅ `write clone-template-row`, `clone-row-band` | ❌ |
| **Sessions** | ⚠ implicit (per-process global state) | ✅ explicit, event-sourced, with fork/undo/redo | ❌ per-call (Task 08 caches results, not workbook) |
| **Dry-run preflight** | ❌ | ✅ `analyze ref-impact`, `style-batch preview` | ❌ |
| **Verification / proof** | ❌ | ✅ `verify proof`, `verify diff` (target proof + change diff) | ❌ |

#### 3.3 Token-efficiency defaults

| | MotherDuck MCP | PSU3D0 | In-house |
|---|---|---|---|
| **Default response cap (rows)** | 1024 | varies per tool, max-cells = 10 000 | 200 (xls_query) / unbounded (read_file) |
| **Default response cap (chars)** | 50 000 | byte cap = 65 536 (64 kB) | 1 MB offload threshold (PR #242) |
| **Schema-first by default** | ❌ (model writes SQL directly) | ✅ (`read overview` lightweight by design) | ✅ (`xls_describe` first per skill prompts) |
| **Auto-pagination** | ✅ (cap row count) | ✅ (`truncated: true` + `next_offset`) | ⚠ Task 28 row_limit; manual via SQL `LIMIT` |
| **Compact format default** | ⚠ JSON only | ✅ CSV/values default; verbose opt-in | ⚠ Task 07 trims xlsx; Task 28 returns JSON rows |
| **Suppresses null runs** | n/a (SQL returns only matching rows) | ✅ via region scoping | ✅ via Task 07 |
| **Strips boilerplate** | n/a | ✅ separate read/write tools | ✅ via Task 07 / Task 29 |
| **Uniform server-level switch** | `--max-rows`, `--max-chars` (CLI flags) | `output_profile=token_dense` server config | per-task feature flags |

#### 3.4 Reads, writes, reversibility

| Capability | MotherDuck MCP | PSU3D0 | In-house |
|---|---|---|---|
| **Cross-sheet SQL JOINs** | ✅ via `read_xlsx` CTE per sheet | ❌ no SQL | ✅ via `xls_query` CTEs |
| **Aggregations (MAX, MIN, AVG, GROUP BY)** | ✅ deterministic | ❌ model-side compute | ✅ deterministic |
| **Window functions / CTEs** | ✅ | ❌ | ✅ |
| **Cross-file analytics** | ✅ ATTACH multiple files | ❌ one workbook per session | ⚠ via `xls_query` with multiple `read_xlsx` calls in CTE |
| **Write fidelity (preserves formulas)** | ❌ COPY TO rewrites file | ✅ in-place edits via umya-spreadsheet | ✅ exceljs preserves cells outside change set |
| **Write fidelity (preserves formats/styles/charts)** | ❌ | ✅ | ⚠ exceljs preserves most; charts limited |
| **Undo / redo** | ❌ | ✅ event-sourced session log | ❌ |
| **Fork / checkout / merge** | ❌ | ✅ session fork lifecycle | ❌ |
| **Dry-run before apply** | ❌ | ✅ `analyze ref-impact`, `style-batch preview` | ❌ |
| **Proof of effect (target verification)** | ❌ | ✅ `verify proof` | ❌ |
| **Diff (before/after)** | ❌ | ✅ `verify diff` | ❌ |
| **Reversibility primitive (recover compacted bytes)** | ❌ | ✅ via session log | ⚠ Task 26 `fetch_raw` (per-result, less rich) |

#### 3.5 Cache scope

This is the **single most important architectural axis** because it directly determines Problem #1's outcome.

| Cache level | MotherDuck MCP | PSU3D0 | In-house (current Task 08) |
|---|---|---|---|
| Per-call (`(toolName, args)`) | ❌ | ❌ | ✅ |
| Per-workbook (load once, query many) | ⚠ DuckDB caches parsed columnar data per process; relies on user keeping connection open | ✅ explicit sessions | ❌ (Task 08 misses different-args calls) |
| Per-chat | ❌ (per-process global) | ⚠ session export/import needed | ✅ keyed by `chatId` |
| Persistent across restarts | ⚠ if `--db-path` is a file | ⚠ via `session export` | ✅ SQLite-backed |
| mtime-keyed invalidation | ⚠ user must re-attach | ✅ session detects file change on materialize | ✅ Task 08 + Task 28 keyed by mtime |
| Cross-process / cross-instance | ❌ | ❌ | ⚠ not designed |

**Key insight:** PSU3D0's session model is the only one that **caches at the workbook level** — the level that actually matches the user pattern (same file, different ranges across calls). Our Task 08 cache is the wrong level; it should be evolved to a workbook-level cache modeled on PSU3D0's sessions.

#### 3.6 Maturity & maintenance

| | MotherDuck MCP | PSU3D0 | In-house |
|---|---|---|---|
| **Maintainer** | MotherDuck team (commercial) | Solo (Frankie Colson) | DC team |
| **Release cadence** | Weekly-ish | Weekly until April | Aligned with DC sprints |
| **Test coverage** | FastMCP test suite + DuckDB upstream | Tested per-region heuristics; broader suite via parity-harness.js | new — full suite TBD |
| **Documented limitations** | DuckDB SQL surface = its limitations | `docs/HEURISTICS.md` honest about heuristic-corner-cases | TBD |
| **Production stability signal** | High (DuckDB is mature; MotherDuck team behind) | Medium-high (active, Apache-2.0, tests) | Internal control |
| **Stack risk** | Tied to FastMCP framework + Python ecosystem | Tied to PSU3D0's umya-spreadsheet fork (specific commit pinned) | Tied to DuckDB native module + exceljs |

#### 3.7 License compatibility

| | License | Compatible with DC's closed-source Electron build? |
|---|---|---|
| MotherDuck MCP | MIT | ✅ |
| PSU3D0 | Apache-2.0 | ✅ (with attribution) |
| In-house | n/a (we own it) | ✅ |
| DuckDB (native + WASM) | MIT | ✅ |
| exceljs | MIT | ✅ |
| umya-spreadsheet (PSU3D0's fork) | MIT | ✅ |

All three options are license-clean for DC's distribution model.

### 4. Failure modes & edge cases

#### 4.1 What breaks under each candidate

**MotherDuck MCP failures:**
- Bad SQL → DuckDB error message returned (model can self-correct).
- xlsx with merged cells → DuckDB parses with NULLs in merged-region cells (no error, silent data quality issue).
- Multi-table sheet → `read_xlsx` reads from `A1` to last non-empty, mashing tables together. Model has no way to detect this.
- Writes to xlsx → `COPY TO` produces a fresh file; **silently strips formulas, formatting, charts, comments, conditional formats, named ranges, defined data validations**. Catastrophic for "edit user's existing financial model."
- Connection switching (`--allow-switch-databases`) lets the model attach arbitrary local `.duckdb` files → security exposure for shared DC instances; gate it.

**PSU3D0 failures:**
- Native binary crash on uncommon xlsx variant → stderr surfaces, model gets opaque error.
- Region detection on simple flat tables → may classify as `likely_metadata` or `unknown` due to heuristic bias toward financial-spreadsheet test corpus (per `docs/HEURISTICS.md`).
- Sessions across MCP server process restarts → session_id invalid; state lost unless `session export` was called. DC's auto-update would orphan sessions.
- 4-binary distribution problem for MCPB embedding (~120 MB bundle) OR experimental WASM (partial capabilities).
- No SQL means no analytical Q&A → degraded user experience for "what's the highest expense" pattern.

**In-house plan failures:**
- DuckDB native dependency on Electron build → platform-specific prebuilds must work on every supported host; macOS arm64 + x64 + Windows + Linux. (DuckDB-WASM avoids this.)
- exceljs known limitation: large workbooks (>100 MB) load slowly; whole-workbook in-memory.
- Multi-table detection algorithm not yet ported from PSU3D0; likely 80% accurate at first ship, needs iteration.
- Cache invalidation event bus must reach all subscribers reliably (tests required).
- Skill prompt updates lag the tool ship → models keep using `read_file(xlsx)` until skills updated; Task 29 hint mitigates but doesn't eliminate.

#### 4.2 Where each candidate is *blind*

| Blind spot | MotherDuck | PSU3D0 | In-house |
|---|---|---|---|
| Excel-specific structure (multi-table, named ranges, formulas) | ❌ | ✅ aware | ⚠ partial via exceljs |
| Batched writes preserving fidelity | ❌ silent fidelity loss | ✅ | ✅ |
| N+1 read antipattern across calls | ⚠ caches in DuckDB process; calls still cost | ✅ session = automatic dedup | ⚠ Task 08 doesn't dedupe different ranges |
| Cross-chat / persistent state | ❌ per-process | ⚠ session export needed | ✅ SQLite |
| Untracked LLM usage (F1) | ❌ orthogonal | ❌ orthogonal | ⚠ Task 03 |
| Skill prompt routing (Task 29) | ❌ | ❌ | ✅ |
| Structural change preflight | ❌ | ✅ `analyze ref-impact` | ❌ |

### 5. Pros & cons

#### 5.1 MotherDuck MCP

**Pros:**
1. **Lowest engineering cost.** Already shipping as `.mcpb`. Just add to DC's mcp-config and ship a skill prompt. Hours, not weeks.
2. **DuckDB SQL is the most-trained-by-LLMs query language.** Models write correct DuckDB SQL > 95 % of the time given column names from `list_columns`.
3. **Coverage of analytical Q&A is unbounded.** Every aggregation, filter, join, window function is in scope.
4. **Maintained by the DuckDB / MotherDuck team.** High signal of long-term durability.
5. **Generic surface — works across xlsx, csv, parquet, json, S3 files.** One MCP for tabular data analytics.
6. **Built-in caps (1024 rows, 50 000 chars) prevent bytes runaway.**
7. **Read-only by default;** `--read-write` opt-in. Good security posture.

**Cons:**
1. **Doesn't solve Problem #1 (N+1 reads).** DuckDB caches per-process columnar parse results, but 130 SQL roundtrips for 130 rows still cost 130 calls.
2. **Doesn't solve Problem #3 (model-swap re-probe).** No session model; new model gets fresh state.
3. **Write fidelity catastrophic for xlsx** — `COPY TO` strips formulas, formatting, charts, named ranges. Cannot edit a user's existing financial model in place.
4. **No Excel-aware tools.** No region detection, no named ranges, no formula introspection, no batch writes that preserve format.
5. **No reversibility primitive.** Once a write goes through, no undo.
6. **No multi-table-per-sheet detection.** `read_xlsx` reads `A1` to last non-empty cell, mashing tables.
7. **Generic surface = Excel ergonomics suffer.** Model has to write SQL even for "what sheets exist?" (vs just reading metadata).
8. **External MCP process** — adds another process to DC's runtime, IPC overhead, error surface.

**Tradeoffs (when to pick):**
- ✅ When users do **mostly analytical Q&A on read-only Excel**.
- ✅ When fast time-to-ship matters more than fidelity-preserving writes.
- ❌ When users edit their existing financial models (write fidelity loss is unacceptable).
- ❌ When you want to solve Problem #1 (N+1) — this doesn't.

#### 5.2 PSU3D0

**Pros:**
1. **Best architectural answer to Problem #1 (workbook-level sessions).** Genuinely better than any per-call cache.
2. **Multi-table-per-sheet detection shipped + tested.** Documented heuristics in `docs/HEURISTICS.md`.
3. **Reversibility (event-sourced log, fork/undo/redo) built-in.** Strictly better than per-result `fetch_raw`.
4. **Preflight verification (`analyze ref-impact`, `verify proof`, `verify diff`)** prevents whole-workbook re-reads after edits.
5. **Token-efficiency defaults at server level (`output_profile=token_dense` + 64 kB cap).** Single switch, applies everywhere.
6. **Excel-aware ergonomics.** Named ranges CRUD, formula trace, ARGB color normalization, ARGB hex warnings, table-aware append, template row cloning.
7. **Skill prompts shipped** (`EXPLORE_SKILL.md`, `SAFE_EDITING_SKILL.md`, `CLI_BATCH_WRITE_SKILL.md`) — saves writing them ourselves.
8. **In-place writes preserve formulas, formats, charts, named ranges.** umya-spreadsheet does the right thing.
9. **Apache-2.0 license is permissive.** We can copy ideas freely.

**Cons:**
1. **No SQL.** Analytical Q&A degrades to model-side compute over `read table` results. "Highest expense" requires reading the column and reasoning row-by-row; SQL would return one number.
2. **Native Rust binary distribution.** 4 platform binaries (~30 MB each) for true cross-platform = ~120 MB MCPB.
3. **WASM target is experimental and unpacked.** Capability matrix is partial (no `structureBatch`, no `replaceInFormulas`, no `verification`, no `forkLifecycle`, no `staging`). Would require us to package and publish it.
4. **Solo maintainer, slowing cadence.** Last push 2026-04-01; medium-term sustainability unclear.
5. **Heuristics tested against single financial-spreadsheet corpus.** Documented in `docs/HEURISTICS.md` — may misclassify simple flat tables, pivot tables, formatted-only sheets.
6. **No merged-cell support yet.** Real-world spreadsheets break this often.
7. **Session lifecycle requires orchestration on DC's side** — auto-update + crash recovery means we need to call `session export` proactively or accept session loss.
8. **Tool surface is large (~50 tools) — model needs to learn them all.** Some are redundant with MCP-level tools (e.g. `workbook copy` vs filesystem move).

**Tradeoffs (when to pick):**
- ✅ When users do heavy structural / formula-preserving edits on financial models.
- ✅ When reversibility (undo, fork, dry-run) is critical for safety.
- ❌ When SQL analytical Q&A is the primary workflow.
- ❌ When platform-agnostic single-artifact distribution is mandatory and we can't take on WASM packaging burden.

#### 5.3 In-house plan (Tasks 24/28/29)

**Pros:**
1. **Combines SQL (DuckDB) with structured writes (exceljs).** Best of both functional worlds.
2. **Integrated into DC** — no external MCP process, no IPC, no separate distribution.
3. **Tailored to actual user problems** documented in `EXCEL_USAGE_REVIEW.md`.
4. **Soft-deprecation hint (Task 29)** routes the model away from `read_file(xlsx)` automatically.
5. **Cache invalidation hook** designed end-to-end (event bus + mtime-keying).
6. **Ports the best ideas from MotherDuck (SQL) + PSU3D0 (region detection, output_profile)** without the integration costs.
7. **Owns the maintenance** — no upstream dependency risk.
8. **Platform-agnostic via Node.js + DuckDB native (npm prebuilds) or DuckDB-WASM.**

**Cons:**
1. **Highest engineering cost (~3-4 weeks across P0+P1 task waves).**
2. **Task 08's per-call cache is the wrong level.** PSU3D0's session model is strictly better; we need to learn this lesson and rework Task 08.
3. **Multi-table detection algorithm not yet ported.** ~500-800 LOC + iteration to match PSU3D0's quality.
4. **No reversibility / undo / preflight.** Task 26 `fetch_raw` is a poor man's version of session logs.
5. **Skill prompt updates required** for `vc-portfolio-enrichment`, `financial-review`, etc.
6. **Maintenance burden owned by DC team** — DuckDB updates, exceljs updates, our integration code.
7. **Two engines (DuckDB + exceljs) for one feature** — increased surface area for bugs.

**Tradeoffs (when to pick):**
- ✅ When tight integration with DC's local-server / chat lifecycle matters.
- ✅ When we want SQL + write fidelity in one stack.
- ✅ When the soft-deprecation routing is needed (Task 29 only works in-house).
- ❌ When ship-by-Friday is the constraint (this is 3-4 weeks).
- ❌ When we want to outsource long-term maintenance.

### 6. Architecture options

Given the analysis, four realistic paths emerge.

#### Architecture A — Adopt MotherDuck MCP wholesale

**Plan:** Ship MotherDuck `.mcpb` with DC. Update skill prompts to teach SQL-first xlsx workflow. Skip Tasks 24/28/29.

**What you get:** SQL Q&A on xlsx, low-effort. Solves Problem #2 (verbose output) by making queries selective.
**What you lose:** Problem #1 (N+1) unsolved. Problem #3 partially unsolved. Write fidelity catastrophic — can't safely edit user xlsx files.
**Effort:** ~2-3 days (mcp-config + skill prompts).
**Verdict:** Acceptable if users mostly do **read-only analytical Q&A** on xlsx. Unacceptable if they edit existing files.

#### Architecture B — Adopt PSU3D0 wholesale

**Plan:** Embed PSU3D0 binaries (4 platforms) in DC's MCPB OR push WASM packaging upstream. Skip Tasks 24/28/29.

**What you get:** Best Problem #1 + #3 solution (sessions). Region detection. Reversibility. Excel-aware writes.
**What you lose:** SQL analytical Q&A entirely. ~120 MB MCPB or unpackaged WASM with partial capabilities.
**Effort:** ~1 week to integrate binaries + write Node launcher; or ~2-3 weeks to package WASM upstream.
**Verdict:** Acceptable if users mostly do **structural editing of financial models**. Unacceptable for analytical Q&A on flat data.

#### Architecture C — Hybrid: PSU3D0 sessions + DuckDB SQL + our skill routing

**Plan:** Adopt PSU3D0's **session model** in our in-house code (not adopt PSU3D0 itself — port the design). Keep DuckDB-SQL for analytical Q&A. Keep exceljs for cell-level writes. Soft-deprecate `read_file(xlsx)` (Task 29). Build multi-table detection (Task 24) using PSU3D0's algorithm as reference.

**What you get:** Workbook-level cache (Problem #1 fixed). SQL (Problem #2). Structured writes preserving fidelity (Problem #3). Soft-deprecation routing.
**What you lose:** Reversibility / undo / preflight (could add later as Task 30+). Some heavyweight PSU3D0 features (formula-trace, ref-impact) not ported.
**Effort:** ~3-4 weeks (similar to current Tasks 24/28/29, but Task 08 reworked from per-call cache to workbook-session cache).
**Verdict:** **Recommended.** Solves all three user problems. Avoids binary distribution. Owns the integration. Defers reversibility/preflight to a follow-up.

#### Architecture D — In-house plan as currently designed (Tasks 24/28/29 + Task 08 per-call cache)

**Plan:** Ship as-is per `EXCEL_USAGE_REVIEW.md` prioritized fix plan.

**What you get:** SQL + structured writes + multi-table detection + soft-deprecation.
**What you miss:** Task 08's per-call cache misses N+1 with different ranges (the actual `ef6c1e26` pattern). Workbook-level caching not designed in.
**Effort:** ~3-4 weeks as planned.
**Verdict:** **Materially weaker than Architecture C** because Task 08's cache is the wrong level. Don't ship this without first reworking Task 08 to be workbook-level.

### 7. Decision framework

| If user activity profile is mostly... | Then pick... |
|---|---|
| Read-only analytical Q&A on flat tables, fast ship | A (MotherDuck MCP) |
| Structural editing of financial models, write fidelity critical | B (PSU3D0) |
| Mix of both, integrated DC experience | **C (hybrid in-house with workbook-level cache)** |
| Same as above but accept materially weaker N+1 handling | D (current Task plan) |

`EXCEL_USAGE_REVIEW.md` data shows users do **both** — `cfbfd7a2` is analytical Q&A on a financial model; `ef6c1e26` is enrichment writes; `e2b70ff2` is PDF→Excel construction. Architecture C is the only one that covers all three.

### 8. Recommendation

**Ship Architecture C.** Specifically:

1. **Replace Task 08's per-call cache design with a workbook-level session cache** modeled on PSU3D0's session model.
   - Cache key: `(chatId, path, mtime)`.
   - Value: parsed exceljs Workbook + DuckDB connection with the xlsx registered.
   - Lifetime: chat scope (with mtime invalidation on writes).
   - Rationale: the actual `ef6c1e26` antipattern issues different ranges per row → per-call cache misses every time → 201 file-parses. Session-style cache makes this 1 parse.

2. **Adopt MotherDuck MCP's SQL surface design** in [Task 28](./tasks/28-xls-query-duckdb.md):
   - Single `xls_query(path, sheet?, range?, sql)` tool (already aligned).
   - 1024-row + 50 000-char default caps (steal from MotherDuck).
   - Read-only by construction; writes go through `xls_write`.

3. **Port PSU3D0's multi-table detection algorithm** (Task 24's `xls_describe`):
   - Region kinds: `likely_data | likely_table | likely_parameters | likely_calculator | likely_outputs | likely_metadata | unknown`.
   - Confidence score per region.
   - Rationale: `cfbfd7a2`'s financial model has multiple tables per sheet that the model needs to disambiguate.

4. **Adopt PSU3D0's `output_profile=token_dense` server-level switch** instead of per-tool Task 07 / Task 23 / Task 25 flags.
   - Single `effectiveness.token_dense_outputs` flag flips defaults for all tool responses.
   - Per-call opt-out via `output_profile: "verbose"` arg.

5. **Add a follow-up Task 30 — event-sourced session ops + `analyze ref-impact` preflight** to land PSU3D0's reversibility lessons later. Not blocking the P0/P1 ship.

6. **Ship Task 29 (read_file xlsx soft-deprecation)** unchanged — neither MotherDuck nor PSU3D0 displaces `read_file`; the routing nudge is still needed.

**Do not adopt MotherDuck or PSU3D0 wholesale** as MCPB-injected MCPs in DC. Reasons:
- MotherDuck's write fidelity is unacceptable.
- PSU3D0's binary distribution is operationally costly; WASM unpackaged.
- Both are external processes; in-house is integrated with DC's chat lifecycle and Task 29 routing.

**Do borrow ideas heavily.** All three concrete recommendations above (workbook-level sessions, default caps, multi-table detection, output profile) are direct ports of design lessons from MotherDuck + PSU3D0.

### 9. Action items if Architecture C is selected

| Item | Task | Change required |
|---|---|---|
| Rework Task 08 to workbook-level cache | [08](./tasks/08-per-chat-tool-result-cache.md) | Replace `(toolName, args)` cache with `(chatId, path, mtime)` workbook cache; reads against any range hit the cached parse. |
| Port PSU3D0's region-detection algorithm | [24](./tasks/24-xls-first-class-tools.md) | Already specified; keep as-is. |
| Add server-level `token_dense` profile | new amendment to [07](./tasks/07-trim-verbose-xlsx-output.md) | Promote per-tool flag to server-level config; per-call opt-out. |
| Adopt 1024 / 50 000 default caps in `xls_query` | [28](./tasks/28-xls-query-duckdb.md) | Already specified at `row_limit = 200`; bump to 1024 to match MotherDuck. |
| Plan reversibility / preflight follow-up | new Task 30 | Document for after P1 ships; not blocking. |
| Ship soft-deprecation hint | [29](./tasks/29-read-file-xlsx-soft-deprecation.md) | Already specified; keep as-is. |
| Update `EXCEL_USAGE_REVIEW.md` ship plan | [EXCEL_USAGE_REVIEW.md](./EXCEL_USAGE_REVIEW.md) | Note: Task 08 reworked to workbook-level; reference this doc. |

### 10. Cross-references

- [EXCEL_USAGE_REVIEW.md](./EXCEL_USAGE_REVIEW.md) — fleet-wide Excel-user evidence (1 753 users, 33 % hit token-consumption problems) and prioritized fix plan.
- [EXCEL_MCPS_RESEARCH.md](./EXCEL_MCPS_RESEARCH.md) — broader 15-MCP landscape research; this doc is the deep dive on the DuckDB-aware subset + PSU3D0 + in-house.
- [Task 08](./tasks/08-per-chat-tool-result-cache.md) — per-chat tool-result cache (recommend rework to workbook-level).
- [Task 24](./tasks/24-xls-first-class-tools.md) — first-class XLS tools; multi-table detection.
- [Task 28](./tasks/28-xls-query-duckdb.md) — `xls_query` via embedded DuckDB SQL.
- [Task 29](./tasks/29-read-file-xlsx-soft-deprecation.md) — soft-deprecate `read_file(xlsx)`.
- [Task 26](./tasks/26-fetch-raw-primitive.md) — reversibility primitive (consider evolving toward session log).
- [SUMMARY.md](./SUMMARY.md) — fleet-wide effectiveness investigation.
- MotherDuck MCP — https://github.com/motherduckdb/mcp-server-motherduck
- PSU3D0 — https://github.com/PSU3D0/spreadsheet-mcp
- DuckDB — https://duckdb.org · `read_xlsx` extension docs
- exceljs — https://www.npmjs.com/package/exceljs
