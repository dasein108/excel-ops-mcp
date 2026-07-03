---
title: "Project-Scoped excel_ops Skill"
status: done
phase: P1
---

# Task 17 — Project-Scoped `excel_ops` Skill

Create a project-scoped Codex skill that teaches agents how to use the `excel-ops` CLI for Excel work in this repository when MCP is unavailable or unnecessary.

## Skill Location

Create the skill under the current project:

```text
.codex/skills/excel-ops/
```

The folder name should be `excel-ops` to satisfy Codex skill naming rules. The skill description can mention the user-facing alias `excel_ops`.

## Scope

- Use for local Excel `.xlsx` work in this project.
- Prefer CLI commands over ad hoc Python scripts.
- Read/describe/query first.
- Dry-run before commit.
- Save edited workbooks to new files by default.
- Do not cover Google Sheets or Numbers.

## Required Skill Files

```text
.codex/skills/excel-ops/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    └── cli-workflows.md
```

Do not add README or extra docs.

## SKILL.md Requirements

Frontmatter:

```yaml
---
name: excel-ops
description: Use for Excel operations in this repository through the local excel-ops CLI when Codex needs to inspect, query, summarize, validate, or safely edit .xlsx workbooks without relying on an MCP server. Supports workbook describe, DuckDB SQL reads, targeted range reads, staged dry-run writes, diffs, and commit-to-new-file workflows for bookkeeping, accounting, marketing operations, SEO, and research spreadsheets.
---
```

Body should stay concise and include:

- Always start with `excel-ops sheets`, then `excel-ops tables`.
- Prefer `excel-ops query` for tabular analysis.
- Use `excel-ops read-range` only for exact inspection.
- Use `excel-ops write` for dry-run staging.
- Use `excel-ops diff` before `excel-ops commit`.
- Never overwrite the source workbook unless explicitly requested.
- For complex examples, read `references/cli-workflows.md`.

## Reference Requirements

`references/cli-workflows.md` should include practical workflows:

- Summarize a workbook.
- Find top vendors/campaigns/keywords.
- Reconcile transactions.
- Inspect formulas.
- Add review notes.
- Commit edits to a new workbook.

## Acceptance Criteria

- Skill is initialized with the official skill init script.
- Skill validates with `quick_validate.py`.
- `agents/openai.yaml` exists and matches the skill.
- Skill instructions mention the current repo CLI command, not a global MCP server.
- Skill does not include Google Sheets or Numbers workflows.

## Notes

Because this is project-scoped, it should live in `.codex/skills`, not the global `$CODEX_HOME/skills`.
