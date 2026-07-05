---
title: "Excel MCP Roadmap — Python Option A"
status: done
scope: excel-only
---

# Excel MCP Roadmap — Python Option A

Build a standalone Python MCP focused only on Excel workbooks (`.xlsx` first, `.xlsm` read/write with warnings later). Google Sheets and Numbers are intentionally out of scope for this phase.

## Product positioning

The MCP is for financial and operations work: bookkeeping, accounting, marketing operations, research, SEO exports, reconciliations, reporting, and spreadsheet-based analysis.

The product should behave like a careful spreadsheet analyst:

- Describe before reading bulk data.
- Query with SQL instead of dumping rows.
- Dry-run before writing.
- Preserve formatting and formulas where practical.
- Produce auditable diffs and source citations.
- Avoid row-by-row tool loops.

## Architecture

Core stack:

- Python MCP server.
- `duckdb` for in-memory SQL reads.
- `openpyxl` for Excel workbook parsing and writes.
- SQLite for persistent metadata/session cache.
- In-memory LRU for hot workbook sessions.

Primary flow:

```text
spreadsheet_open(path) -> session_id
spreadsheet_describe(session_id) -> regions/schema/formulas/source ranges
spreadsheet_query(session_id, sql) -> compact SQL result
spreadsheet_write(session_id, ops, dry_run=true) -> staged preview
spreadsheet_commit(session_id, output_path?) -> saved workbook + diff
```

## Planned Tasks

| Task | Title | Phase |
|---|---|---|
| 01 | Python MCP package foundation | P0 |
| 02 | Excel session registry and cache | P0 |
| 03 | Excel workbook describe | P0 |
| 04 | Region and header detection | P0 |
| 05 | DuckDB table materialization and SQL query | P0 |
| 06 | Targeted range inspection | P1 |
| 07 | Structured batch write operations | P1 |
| 08 | Dry-run, staging, commit, and diff | P1 |
| 09 | Audit log and source citation model | P1 |
| 10 | Token efficiency, caps, and anti-loop telemetry | P2 |
| 11 | Financial operations recipes and examples | P2 |
| 12 | Workbook fidelity and regression fixtures | P2 |
| 13 | Public tool contracts and JSON schemas | P0 |
| 14 | Security and filesystem sandbox policy | P0 |
| 15 | Implementation milestones and release gates | P0 |
| 16 | Excel CLI alternative | P1 |
| 17 | Project-scoped `excel_ops` skill | P1 |
| 18 | CLI parity tests against MCP tool layer | P1 |
| 19 | CLI usage recipes for operations work | P2 |
| 20 | User README and install guide | P1 |
| 21 | Developer publishing guide | P1 |
| 22 | GitHub release to PyPI automation | P1 |
| 23 | Agent-agnostic Excel Ops skill guidance | P1 |

## Explicit Non-Goals

- Google Sheets support.
- Apple Numbers support.
- Full Excel calculation engine.
- Full chart/pivot/table reconstruction.
- SQL writes back to Excel.
- UI automation of Excel.

## Key Design Constraints

- `spreadsheet_query` must be read-only.
- Writes must be structured operations, not arbitrary Python or SQL.
- Writes must default to `dry_run=true`.
- Session cache must be workbook-level, not tool-call-level.
- Every read response should include source references such as `file.xlsx#Sheet!A1:F20`.
- Every large response must be capped and paginated or summarized.

## Build Order

1. Task 13: lock the public JSON contracts first.
2. Task 01: create package and placeholder tools.
3. Task 14: implement path and sandbox safety before file reads.
4. Task 02: implement sessions and workbook cache.
5. Task 03: implement workbook describe.
6. Task 04: add region/header detection to describe.
7. Task 05: materialize regions into DuckDB and enable SQL.
8. Task 12: create fixture workbooks and regression harness early.
9. Task 06: add exact range inspection.
10. Task 07: add write operation validation and staging.
11. Task 08: add dry-run/commit/diff.
12. Task 09: persist audit logs and source citations.
13. Task 10: add telemetry and anti-loop warnings.
14. Task 11: add domain recipes and usage examples.
15. Task 15: package release gates and acceptance.
16. Task 16: add the CLI alternative over the same core tool layer.
17. Task 18: verify CLI parity with direct tool calls.
18. Task 17: create the project-scoped `excel_ops` skill that uses the CLI.
19. Task 19: add practical CLI recipes for financial operations workflows.
20. Task 20: add user-facing README with `uvx` install path.
21. Task 21: add developer publishing guide.
22. Task 22: automate PyPI publishing from GitHub releases.
23. Task 23: keep the skill agent-agnostic and backed by shared instructions.

## First Usable Milestone

The first useful release is read-only:

```text
spreadsheet_open
spreadsheet_describe
spreadsheet_query
```

That is enough for bookkeeping, accounting, marketing, SEO, and research users to inspect workbooks, find issues, summarize tables, run reconciliations, and answer analytical questions without dumping raw sheets into the model.

## First Write Milestone

The first write release should include:

```text
spreadsheet_write(dry_run=true)
spreadsheet_commit(output_path=...)
spreadsheet_diff
```

Do not ship writes without dry-run and diff.

## CLI and Skill Milestone

The CLI and skill are an alternative access path for Codex when an MCP server is not running:

```text
excel-ops open workbook.xlsx
excel-ops describe --session ses_...
excel-ops query --session ses_... --sql "select ..."
excel-ops read-range --session ses_... --sheet Sheet1 --range A1:F20
excel-ops write --session ses_... --ops ops.json
excel-ops diff --session ses_... --staged stg_...
excel-ops commit --session ses_... --staged stg_... --output out.xlsx
```

The project-scoped skill should teach Codex to prefer this CLI for Excel work in this repository when MCP is unavailable or when deterministic shell workflows are more convenient.

## Distribution Milestone

The first public distribution target is PyPI:

```bash
uvx excel-mcp
uvx --from excel-mcp excel-ops sheets workbook.xlsx
```

GitHub releases should publish to PyPI through trusted publishing, not checked-in API tokens.

## Later Additions (Tasks 24–29)

Added after the original 00–23 plan. Kept in this same backlog so there is one list.

- Task 24: computed value resolution (cached + recompute fallback). [done]
- Task 25: eval harness — subagent answerer + judge. [draft]
- Task 26: SaaS model eval suite (20 questions + gold + deterministic checks). [draft]
- Task 27: agent-understandability rules — matrix orientation + formula-lineage trace. [done]
- Task 28: tag-driven PyPI release. [partial] — folded in from a superpowers design spec.
- Task 29: cross-agent installer. [draft] — folded in from a superpowers design spec.

Design specs that used to live under `docs/superpowers/specs/` are now folded into this
`tasks/` backlog (Tasks 28–29) so there is a single source of truth.
