---
title: "Agent-Agnostic Excel Ops Skill Guidance"
status: done
phase: P1
---

# Task 23 — Agent-Agnostic Excel Ops Skill Guidance

Update `.codex/skills/excel-ops` so the skill is usable as an agent-agnostic workflow guide and refers to shared repository docs where possible.

## Scope

- Keep Codex skill format valid.
- Avoid Codex-only assumptions in the body.
- Point to shared README/development docs for commands and maintenance rules.
- Keep CLI workflow reference concise.

## Acceptance Criteria

- Skill validates.
- Skill still triggers for Excel `.xlsx` CLI workflows.
- Skill refers to `README.md`, `AGENTS.md`, and `references/cli-workflows.md` as shared guidance.
- Skill body says the CLI is the source of truth for deterministic agent workflows.

