---
title: "Eval Harness — Subagent Answerer + Judge"
status: draft
scope: evals
---

# Eval Harness — Subagent Answerer + Judge

A repeatable way to measure how well an agent can answer questions about an `.xlsx`
using **only** the excel-ops skill / Excel MCP tools — no bespoke scripts, no
pandas/openpyxl by hand.

## Requirement (from the brief)

- Run N questions against a workbook, store the agent's answers.
- Compare answers to pre-computed gold results.
- The **answering** pass must know nothing about the gold answers and work entirely
  from scratch through mcp/skill tools.
- If a tool is missing to answer a question, add it to the MCP/CLI, update docs and
  references, and add rules to the skill (see task 24 for the first such gap:
  computed values).

## Shape

Three isolated roles so the answerer can't peek at gold:

```
                 evals/<suite>/questions.jsonl   (id, question, [range hints])
                                  │
        ┌─────────────────────────┼──────────────────────────┐
        ▼                         ▼                            ▼
  1. GOLD BUILDER          2. ANSWERER (per Q)          3. JUDGE (per Q)
  deterministic:           fresh subagent,              compares answer vs gold,
  excel-ops CLI/MCP        ONLY excel-ops skill,        tolerant numeric match,
  computes gold values     no gold in context           emits pass/fail + reason
        │                         │                            │
        ▼                         ▼                            ▼
  evals/<suite>/gold.jsonl  evals/<suite>/runs/<ts>/    evals/<suite>/runs/<ts>/
                            answers.jsonl                report.json + report.md
```

### 1. Gold builder
- Deterministic. Uses `excel-ops query` / `read-range --include values` only.
- Produces `gold.jsonl`: `{id, expected, unit, tolerance, source_ref}`.
- Committed once, reviewed by a human. Regenerate only when the fixture changes.

### 2. Answerer (the actual eval subject)
- One `Agent` subagent per question (or a Workflow fan-out).
- System prompt: "Answer using ONLY the excel-ops skill / Excel MCP tools. Do not
  write ad hoc scripts. Return a single JSON `{answer, source_ref, tool_calls}`."
- Given: workbook path + question text. **Not** given: gold, tolerances, hints beyond
  the question. Fresh context per question → "knows nothing about results".
- Writes `answers.jsonl`.

### 3. Judge
- One subagent (or code) per question. Inputs: question, gold row, agent answer.
- Numeric: pass if `abs(answer - expected) <= tolerance` (relative for large values).
- Text/enum: normalized equality or LLM-judge for phrasing.
- Emits `{id, verdict: pass|fail, expected, got, reason}` → `report.json` + a
  human `report.md` scoreboard (score, per-question table, failed-tool notes).

## How to run it from Claude Code

Preferred (native, matches "knows nothing"): a runner that uses the `Agent` tool to
spawn the answerer subagents with the excel-ops skill only, then a judge pass. Store
everything under `evals/saas_v1/runs/<timestamp>/`.

Alternative (CI/reproducible): a thin Python runner `evals/run_eval.py` that shells
`excel-ops` for gold, calls the model API for answers/judge, and writes the same
artifacts. Keep the answerer prompt identical so results are comparable.

## Directory layout

```
evals/
  README.md                     # how to run, how to add a suite
  run_eval.py                   # optional deterministic runner
  saas_v1/
    questions.jsonl             # the 20 questions (task 26)
    gold.jsonl                  # committed gold (task 26)
    runs/<timestamp>/
      answers.jsonl
      report.json
      report.md
```

## Acceptance

- A single command produces a scored `report.md` for `saas_v1`.
- Answerer transcripts show only excel-ops/MCP tool calls (grep the tool log).
- Re-running gold builder is deterministic (byte-stable `gold.jsonl`).
- Any question that could not be answered flags the missing capability, which becomes
  a new task in the 24-style "gap → tool → docs → rule" loop.

## Depends on

- Task 24 (computed values) — required for every numeric question.
- Task 26 (the 20-question suite + gold).
- Task 27 (skill rules so the answerer reliably picks the right tool).
