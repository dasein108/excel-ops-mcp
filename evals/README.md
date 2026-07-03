# excel-ops evals

Two evals, measuring two different things:

| Eval | Runner | Model in loop? | Deterministic? | Measures |
|------|--------|----------------|----------------|----------|
| **Deterministic checks** | `run_checks.py` | No | Yes — byte-stable | Does the *tool* return the right structured value? |
| **Agent answerer** | `run_suite.sh` | Yes (isolated `claude` per question) | No — LLM sampling | Can an *agent* figure it out through the tools? |

Use the **deterministic checks** as the correctness gate (CI, regressions): the
answer is a precise number pulled straight from Excel via the engine, so the same
workbook always yields the same structured JSON. Use the **agent answerer** to study
understandability — expect its score to wobble run-to-run because the LLM is stochastic.

## Deterministic checks (primary)

```bash
python evals/run_checks.py --suite evals/saas_v1 --workbook examples/saas.xlsx
```

Each row of `saas_v1/checks.jsonl` declares a deterministic extraction and its
expected value:

```json
{"id":"q01_total_rev_y1","extract":{"type":"sql","sql":"select year_1 as v from dashboard_table_2 where trim(line_item)='Total Revenue'"},"expect":{"value":1458480,"match":"relative","tol":0.005}}
{"id":"q10_rev_mix_y1","extract":{"type":"sql_map","key":"k","val":"v","sql":"…union all…"},"expect":{"values":{"subscriptions":1076400,"services":262080,"usage":120000},"match":"values","tol":0.005}}
```

Extraction types: `sql` (one value aliased `v`), `sql_map` (multiple `k`/`v` rows →
object), `cell` (computed value), `formula` (formula text), `trace` (lineage — formula
+ precedents). Match types: `relative`, `absolute`, `bool`, `values`,
`trace_precedent_sheet`, `trace_formula`, `formula_contains`. Outputs
`checks_answers.json` (structured, sorted → byte-stable) and `checks_report.md`.
`tests/test_checks.py` asserts 20/20 and that two runs are identical.

## Agent answerer (understandability study)

Measure how well an agent can answer using **only** the excel-ops skill / Excel MCP
tools — no ad hoc openpyxl/pandas scripts.

## Layout

```
evals/
  run_eval.py                 # deterministic judge/scorer (gold vs answers)
  saas_v1/
    questions.jsonl           # 20 questions (id, question, kind)
    gold.jsonl                # committed gold values + match rules
    runs/<timestamp>/
      answers.jsonl           # one {id, answer, source_ref, method} per question
      report.json / report.md # produced by run_eval.py
```

## The three roles (why answers stay honest)

1. **Gold builder** — deterministic. Gold values were computed *only* with
   `excel-ops query` / `read-range --include values` and recorded in `gold.jsonl`
   with a `source_ref`. Regenerate any value by re-running its recorded command.
2. **Answerer** — a fresh subagent per question. Sees only the workbook path + the
   question, and is told to use **only** the excel-ops CLI/MCP. It never sees gold,
   tolerances, or other answers. Writes `answers.jsonl`.
3. **Judge** — `run_eval.py`. Compares answers to gold with tolerant matching
   (relative/absolute numeric, percent-or-fraction, enum, token groups). Never opens
   the workbook.

## Run it — one command (strict per-question isolation)

```bash
evals/run_suite.sh                         # suite=saas_v1, workbook=examples/saas.xlsx
evals/run_suite.sh evals/saas_v1 examples/saas.xlsx
ANSWERER_MODEL=claude-opus-4-8 evals/run_suite.sh   # override answerer model
EVAL_CONCURRENCY=4 evals/run_suite.sh               # run answerers in parallel
```

`run_suite.sh` spawns **one isolated `claude -p` session per question** — fresh
context, tools limited to Bash/Read/Write/Glob/Grep, excel-ops CLI only, and no gold
in scope. Each answerer writes `runs/<ts>/parts/<id>.json`; the script assembles
`answers.jsonl` and runs the judge. This is the strict mode: no answerer can see any
other question or any gold value.

Requirements: the `claude` CLI on PATH and the project `.venv` (excel-ops installed).
It runs with `--permission-mode bypassPermissions` so the local read-only excel-ops
calls don't prompt — safe here because tools are restricted and the workbook is only
read (writes go to the run dir / new workbooks).

## Run it — manual orchestration (alternative)

### Answerer (from Claude Code — matches the "knows nothing" rule)

Orchestrate one subagent per question with the excel-ops skill only. Prompt each:

> Workbook: `examples/saas.xlsx`. Question: `<question>`. Use ONLY the excel-ops CLI
> (`source .venv/bin/activate && excel-ops ...`). Do not use openpyxl, pandas, or read
> the file any other way. Reply with ONE JSON line:
> `{"id": "<id>", "answer": <value>, "source_ref": "<cell/range>", "method": "<commands used>"}`

Collect the JSON lines into `evals/saas_v1/runs/<timestamp>/answers.jsonl`.

### Judge

```bash
python evals/run_eval.py --suite evals/saas_v1
# or point at a specific run:
python evals/run_eval.py --suite evals/saas_v1 --answers evals/saas_v1/runs/<ts>/answers.jsonl
```

Exit code is 0 only when every question passes. `report.md` is the human scoreboard.

## Adding a suite

1. New `evals/<name>/questions.jsonl`.
2. Build `gold.jsonl` with excel-ops commands only; record `source_ref` per row.
3. Run the answerer + judge as above.

If a question can't be answered through excel-ops, that's a **capability gap**: add the
tool to the MCP/CLI, update `SKILL.md` + references, add a rule, then re-run. (The
computed-values gap found by this suite became task 24.)
