---
title: "Implementation Milestones and Release Gates"
status: done
phase: P0
---

# Task 15 — Implementation Milestones and Release Gates

Define the milestone gates for shipping the Excel MCP incrementally.

## Milestone 1 — Read-Only Alpha

Includes:

- Task 01 package foundation
- Task 13 schemas
- Task 14 safety policy
- Task 02 sessions
- Task 03 describe
- Task 04 regions
- Task 05 SQL query

Exit criteria:

- Can open `.xlsx`.
- Can describe sheets and regions.
- Can query detected regions with DuckDB SQL.
- Blocks mutating SQL.
- Handles large sheets with caps.
- Has at least 5 fixture workbooks.

## Milestone 2 — Analyst Beta

Includes:

- Task 06 targeted range inspection
- Initial Task 10 telemetry
- Initial Task 11 examples
- Expanded Task 12 fixtures

Exit criteria:

- Can inspect formulas and exact ranges.
- Can answer bookkeeping/accounting/marketing/SEO examples without raw sheet dumps.
- Emits cache and token-efficiency telemetry.
- Warns on repeated small range reads.

## Milestone 3 — Safe Write Beta

Includes:

- Task 07 structured writes
- Task 08 dry-run/commit/diff
- Task 09 audit log

Exit criteria:

- Writes default to dry-run.
- Commit saves to a new file by default.
- Diff shows direct edits.
- Audit log persists.
- Original files are unchanged after dry-run.
- Formula and formatting fixture tests pass.

## Milestone 4 — Production Candidate

Includes:

- Full Task 10 telemetry.
- Full Task 11 domain examples.
- Full Task 12 regression suite.
- Packaging and install documentation.

Exit criteria:

- CI passes on supported Python versions.
- Tool schemas are stable.
- No known uncapped large responses.
- No known direct source-file overwrite path without explicit opt-in.
- Read-only and write workflows are documented.

## Non-Release Criteria

Do not ship a milestone if:

- Describe can dump unbounded sheet data.
- Query allows mutation.
- Writes can commit without preview.
- Dry-run mutates files.
- Source file overwrite is default.

