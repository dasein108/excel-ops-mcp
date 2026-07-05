# Design: excel-ops MCP v2 — Tool Consolidation & Workflow Optimization

**Date:** 2026-07-05
**Status:** Approved (design), pending implementation plan
**Related backlog:** task 10 (token-efficiency/anti-loop), task 12 (fidelity/regression fixtures), task 13 (public tool contracts), task 18 (CLI parity tests)

## Problem

Two shared runs of the same job (summarize `saas.xlsx` revenue + add a growth row) exposed the MCP path's cost versus a bash/CLI path hitting the same engine:

- **Round-trips.** The stateful workflow forces `open → describe → read_range → write(stage, dry_run) → commit`, ~5 assistant turns. Bash does the equivalent in one stateless shell call.
- **Schema-load tax.** The 10 flat tools load into the harness context in two waves (read set, then the write/commit set), producing two mid-task "loaded tools" stalls.
- **Manual arithmetic tax.** The model summed/averaged raw cells itself, and in the slower run picked the messy source sheet (`Revenue Model`, mixed monthly+annual) instead of the clean one (`Dashboard`, annual). Same answer, more tokens.

Goal: bring the MCP path near bash on tokens and velocity while keeping MCP's edges (typed contracts, filesystem sandbox, no-shell hosts).

## Decisions (locked with user)

1. **Consolidate** the 10 flat tools into ~4 fat, mode-based tools. Accepts a breaking contract change (task 13) and CLI-parity churn (task 18).
2. **Hybrid state:** every tool accepts `path` OR `session_id`. No mandatory `open`; caching preserved.

## Architecture

### Tool surface: 10 → 4

| New tool | Modes / args | Replaces |
|---|---|---|
| `spreadsheet_inspect` | `mode = describe \| read \| trace \| summary`; `source?`, `range`, `cell`, `depth`, `include` | `spreadsheet_describe`, `spreadsheet_read_range`, `spreadsheet_trace` |
| `spreadsheet_query` | `sql`, `limit` | `spreadsheet_query` (unchanged) |
| `spreadsheet_edit` | `ops[]`, `dry_run=false`, `commit=true`, `output_path?`, `overwrite?` | `spreadsheet_write`, `spreadsheet_commit`, `spreadsheet_diff` |
| `spreadsheet_list` | `glob?`, `limit?` | `workbook_list` |

`spreadsheet_open` is removed as a required step. Fewer tools → a single schema-load wave, eliminating the second mid-task stall.

### State model: hybrid (locked)

Each tool takes `path` OR `session_id`:

- `path` → auto-open; a cache hit on an already-open path reuses the warm session.
- Every response echoes `session_id` so follow-up calls on the same workbook skip re-parsing.
- No standalone `open` call in the common flow; caching behavior from the session registry is retained.

```
inspect(path='saas.xlsx', mode='describe')   -> {session_id:'s1', sheets:[...], best_source:...}
inspect(session_id='s1', mode='summary', source='Dashboard!B5:F5') -> {total, mean, max, ...}
edit(session_id='s1', ops=[...], commit=true, output_path='saas.updated.xlsx') -> {saved, diff}
```

### Server-side compute (removes manual-arithmetic tax)

- **`inspect mode=summary`**: server computes total / mean / max / min / YoY-growth over a range or a named row and returns scalars. The model reads results instead of reasoning over raw cells. Chosen over forcing SQL for aggregates because it needs no HogQL/DuckDB knowledge and is one call.
- **`inspect mode=describe` → `best_source` hint**: ranks candidate sheets and flags the clean aggregated sheet vs raw/mixed sheets (the `Dashboard` vs `Revenue Model` distinction). Advisory only; the model may override. Not an auto-select — avoids silently steering to a wrong guess.

### Lean output (task 10)

- `describe` default stays `compact`.
- `summary` / `read` cap returned rows: return a preview plus `truncated: true` and the total row count; never dump an entire sheet.
- `edit` with `commit=true` returns the diff summary inline, removing the separate `diff` round-trip.

### One engine, CLI parity kept (task 18)

- CLI mirrors the same four verbs: `excel-ops inspect | query | edit | list`.
- Old granular CLI subcommands remain as thin aliases for one release, then deprecate.
- CLI-parity tests regenerated against the four-verb surface.

### Migration

- v1 MCP tools retained as **deprecated shims** delegating to v2 for one minor release; deprecation noted in each tool description.
- Task 13 contract doc + JSON schemas rewritten for the four tools.
- Breaking change gated behind a version bump (hatch-vcs tag).

## Testing

- **CLI-parity** (task 18): regenerated for the four verbs; assert CLI and MCP produce identical payloads.
- **Fixture regression** (task 12) on `saas.xlsx`: `inspect mode=summary` must return total `$12,784,732`, max `$3,127,445` (Year 5), mean `$2,556,946`; growth row `+68.8 / +12.0 / +8.0 / +5.0 %`.
- **Round-trip eval**: re-run the shared-A task; assert ≤3 tool calls (baseline 5) and a single schema-load wave.
- **Hybrid state**: `path`-only first call auto-opens and echoes a reusable `session_id`; second call by `session_id` is a cache hit.

## Non-goals

- Not dropping sessions entirely (rejected stateless-only option).
- Not removing DuckDB `query` — kept for ad-hoc SQL.
- No new file formats (`.xlsx` only, unchanged).
- No unrelated refactor of the installer or release tooling.

## Open defaults (picked, low-risk)

- Dedicated `summary` mode rather than forcing SQL aggregates.
- `best_source` as an advisory hint, not auto-select.
- One-release deprecation window for v1 tools and old CLI verbs.
