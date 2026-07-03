#!/usr/bin/env python3
"""Deterministic judge/scorer for excel-ops eval suites.

Reads a suite's ``gold.jsonl`` and a run's ``answers.jsonl``, scores each answer
against gold with tolerant matching, and writes ``report.json`` + ``report.md``.

The *answering* pass (a fresh subagent per question, excel-ops tools only, no gold
in context) is orchestrated separately — see evals/README.md and tasks/25. This
script never sees the workbook; it only compares answers to gold, so it stays cheap
and reproducible.

Usage:
    python evals/run_eval.py --suite evals/saas_v1 --answers evals/saas_v1/runs/<ts>/answers.jsonl
    # defaults to the newest runs/<ts>/answers.jsonl if --answers is omitted
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def to_number(value) -> float | None:
    """Best-effort parse of a numeric answer: handles $, commas, %, and K/M/B suffixes."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().lower().replace(",", "").replace("$", "").replace("usd", "")
    mult = 1.0
    if text.endswith("%"):
        text = text[:-1].strip()
    m = re.search(r"-?\d+(?:\.\d+)?\s*([kmb])?", text)
    if not m:
        return None
    suffix = m.group(1)
    if suffix == "k":
        mult = 1e3
    elif suffix == "m":
        mult = 1e6
    elif suffix == "b":
        mult = 1e9
    try:
        return float(m.group(0).rstrip("kmb ").strip()) * mult
    except ValueError:
        return None


def norm(text) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def judge(gold: dict, answer_raw) -> tuple[bool, str]:
    match = gold.get("match")
    expected = gold.get("expected")
    tol = float(gold.get("tolerance", 0) or 0)

    if match in {"relative", "absolute"}:
        got = to_number(answer_raw)
        if got is None:
            return False, f"could not parse a number from {answer_raw!r}"
        if match == "relative":
            ok = abs(got - expected) <= tol * max(1.0, abs(expected))
        else:
            ok = abs(got - expected) <= tol
        return ok, f"expected {expected} (±{tol}{'rel' if match=='relative' else ''}), got {got}"

    if match == "percent_or_fraction":
        got = to_number(answer_raw)
        if got is None:
            return False, f"could not parse a number from {answer_raw!r}"
        ok = abs(got - expected) <= tol or abs(got - expected / 100.0) <= tol
        return ok, f"expected {expected}% or {expected/100} fraction, got {got}"

    if match == "enum":
        accept = [norm(a) for a in gold.get("accept", [expected])]
        got = norm(answer_raw)
        ok = any(a in got or got in a for a in accept)
        return ok, f"expected one of {accept}, got {got!r}"

    if match == "contains_all_groups":
        got = norm(answer_raw)
        missing = []
        for group in gold.get("groups", []):
            if not any(norm(tok) in got for tok in group):
                missing.append(group)
        return (not missing), (f"all groups present" if not missing else f"missing any-of {missing}")

    return False, f"unknown match type {match!r}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, help="suite dir containing gold.jsonl")
    ap.add_argument("--answers", help="answers.jsonl path (default: newest runs/*/answers.jsonl)")
    args = ap.parse_args()

    suite = Path(args.suite)
    gold_rows = {row["id"]: row for row in load_jsonl(suite / "gold.jsonl")}

    if args.answers:
        answers_path = Path(args.answers)
    else:
        runs = sorted((suite / "runs").glob("*/answers.jsonl"))
        if not runs:
            raise SystemExit("no answers.jsonl found; pass --answers")
        answers_path = runs[-1]
    answers = {row["id"]: row for row in load_jsonl(answers_path)}

    results = []
    for qid, gold in gold_rows.items():
        ans = answers.get(qid)
        if ans is None:
            results.append({"id": qid, "verdict": "missing", "reason": "no answer", "expected": gold.get("expected"), "got": None})
            continue
        ok, reason = judge(gold, ans.get("answer"))
        results.append({
            "id": qid,
            "verdict": "pass" if ok else "fail",
            "reason": reason,
            "expected": gold.get("expected"),
            "got": ans.get("answer"),
            "source_ref": ans.get("source_ref"),
        })

    passed = sum(1 for r in results if r["verdict"] == "pass")
    total = len(gold_rows)
    out_dir = answers_path.parent
    report = {"suite": suite.name, "score": f"{passed}/{total}", "passed": passed, "total": total, "results": results}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    lines = [
        f"# Eval report — {suite.name}",
        "",
        f"**Score: {passed}/{total}**  ·  answers: `{answers_path}`",
        "",
        "| id | verdict | expected | got | note |",
        "|----|---------|----------|-----|------|",
    ]
    for r in results:
        mark = {"pass": "✅", "fail": "❌", "missing": "⚠️"}[r["verdict"]]
        got = str(r.get("got"))
        got = got if len(got) <= 40 else got[:37] + "..."
        lines.append(f"| {r['id']} | {mark} | {r['expected']} | {got} | {r['reason']} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")

    print(f"{suite.name}: {passed}/{total}")
    print(f"wrote {out_dir/'report.md'}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
