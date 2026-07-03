#!/usr/bin/env bash
# One-command eval runner: spawns ONE isolated `claude` answerer per question
# (fresh context, excel-ops tools only, no gold in scope), assembles answers.jsonl,
# then scores with run_eval.py. This is the strict per-question mode from task 25.
#
# Usage:
#   evals/run_suite.sh [suite_dir] [workbook.xlsx]
#   ANSWERER_MODEL=claude-opus-4-8 evals/run_suite.sh          # override model
#   EVAL_CONCURRENCY=4 evals/run_suite.sh                       # parallel answerers
#
# Defaults: suite=evals/saas_v1, workbook=examples/saas.xlsx
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUITE="${1:-$REPO/evals/saas_v1}"
WORKBOOK="${2:-$REPO/examples/saas.xlsx}"
MODEL="${ANSWERER_MODEL:-claude-sonnet-5}"
CONCURRENCY="${EVAL_CONCURRENCY:-1}"
TS="$(date +%Y%m%d-%H%M%S)"
RUN="$SUITE/runs/$TS"
PARTS="$RUN/parts"
mkdir -p "$PARTS"

echo "Suite:     $SUITE"
echo "Workbook:  $WORKBOOK"
echo "Model:     $MODEL   (concurrency $CONCURRENCY)"
echo "Run dir:   $RUN"
echo

answer_one() {
  local id="$1" q="$2"
  local out="$PARTS/$id.json"
  local prompt
  prompt=$(cat <<EOF
You are answering ONE eval question about a spreadsheet using ONLY the excel-ops CLI.
This measures how understandable the workbook is through that tool surface.

Setup: run \`source $REPO/.venv/bin/activate\` then use \`excel-ops ...\`.
Command reference: $REPO/agents/skills/excel-ops/SKILL.md (and references/cli-workflows.md).
Workbook: $WORKBOOK

STRICT RULES:
- excel-ops CLI ONLY. Do NOT use openpyxl, pandas, python to read the xlsx, unzip, or cat the file.
- Do NOT read any gold/answers files. Work it out yourself.
- \`excel-ops read-range <f> --sheet S --range A1:Q1 --include values\` returns COMPUTED numbers for formula cells (add --include formulas to see formula text).
- \`excel-ops query <f> --sql '...'\` is read-only DuckDB; quote table names.
- Layout: row labels in column A; months Jan-Dec = columns B..M; Years 2-5 = columns N..Q. Year totals sum B..M.

Question id: $id
Question: $q

Determine the answer, then WRITE this exact file (overwrite it): $out
Content = ONE line of JSON, nothing else:
{"id":"$id","answer":<number or short string>,"source_ref":"<sheet!cell or range>","method":"<the excel-ops commands you ran>"}
Numeric: plain number, fractions as decimals (0.75). q17 churn: the percent number (2.5). enum/direction/boolean: a short string.
Then reply with just: done
EOF
)
  claude -p "$prompt" \
    --model "$MODEL" \
    --add-dir "$REPO" \
    --permission-mode bypassPermissions \
    --allowedTools Bash Read Write Glob Grep \
    --output-format json > "$RUN/_log_$id.txt" 2>&1 \
    && echo "  ok  $id" \
    || echo "  ERR $id (see $RUN/_log_$id.txt)"
}

# Fan out answerers (bounded concurrency).
running=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  id=$(printf '%s' "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
  q=$(printf '%s' "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["question"])')
  echo "→ $id"
  if [ "$CONCURRENCY" -gt 1 ]; then
    answer_one "$id" "$q" &
    running=$((running+1))
    if [ "$running" -ge "$CONCURRENCY" ]; then wait -n 2>/dev/null || wait; running=$((running-1)); fi
  else
    answer_one "$id" "$q"
  fi
done < "$SUITE/questions.jsonl"
wait

# Assemble answers.jsonl from the per-question parts.
: > "$RUN/answers.jsonl"
for f in "$PARTS"/*.json; do
  [ -f "$f" ] || continue
  if ! python3 -c "import sys,json;print(json.dumps(json.load(open('$f'))))" >> "$RUN/answers.jsonl" 2>/dev/null; then
    echo "  (skipped malformed $f)"
  fi
done

echo
python3 "$REPO/evals/run_eval.py" --suite "$SUITE" --answers "$RUN/answers.jsonl"
