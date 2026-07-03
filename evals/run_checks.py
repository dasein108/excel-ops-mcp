#!/usr/bin/env python3
"""Deterministic, structured eval for excel-ops.

Unlike the LLM answerer (evals/run_suite.sh), this eval has NO model in the loop.
Each check declares a deterministic extraction (a SQL query, a cell read, a formula
read, or a lineage trace) executed straight through the excel-ops engine. Same
workbook + same checks always produce byte-identical structured answers — the value
is a precise number from Excel, not a sampled guess.

It answers the original brief's "compare answers with eval results (pre-processed)"
half: the extraction produces the answer, `expect` is the pre-processed truth, and
the comparison is exact/tolerant but never stochastic.

Usage:
    python evals/run_checks.py --suite evals/saas_v1 --workbook examples/saas.xlsx
Writes checks_answers.json (structured) and checks_report.md next to checks.jsonl.
Exit code 0 iff every check passes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def to_float(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def extract(tools: ExcelMcpTools, session: str, spec: dict) -> dict:
    """Run a check's extraction and return a structured answer dict (deterministic)."""
    kind = spec["type"]
    if kind == "sql":
        r = tools.spreadsheet_query({"session_id": session, "sql": spec["sql"]})
        if not r["ok"]:
            return {"error": r["error"]["message"]}
        rows = r["rows"]
        return {"value": rows[0]["v"] if rows else None, "source": "sql"}
    if kind == "sql_map":
        r = tools.spreadsheet_query({"session_id": session, "sql": spec["sql"]})
        if not r["ok"]:
            return {"error": r["error"]["message"]}
        key, val = spec["key"], spec["val"]
        return {"values": {row[key]: row[val] for row in r["rows"]}, "source": "sql_map"}
    if kind == "cell":
        r = tools.spreadsheet_read_range(
            {"session_id": session, "sheet": spec["sheet"], "range": f"{spec['cell']}:{spec['cell']}", "include": ["values"]}
        )
        if not r["ok"]:
            return {"error": r["error"]["message"]}
        return {"value": r["cells"][0][0]["value"], "source": f"{spec['sheet']}!{spec['cell']}"}
    if kind == "formula":
        r = tools.spreadsheet_read_range(
            {"session_id": session, "sheet": spec["sheet"], "range": f"{spec['cell']}:{spec['cell']}", "include": ["formulas"]}
        )
        if not r["ok"]:
            return {"error": r["error"]["message"]}
        return {"formula": r["cells"][0][0]["formula"], "source": f"{spec['sheet']}!{spec['cell']}"}
    if kind == "trace":
        r = tools.spreadsheet_trace(
            {"session_id": session, "sheet": spec["sheet"], "cell": spec["cell"], "depth": spec.get("depth", 1)}
        )
        if not r["ok"]:
            return {"error": r["error"]["message"]}
        t = r["target"]
        precs = t.get("precedents", [])
        return {
            "formula": t.get("formula"),
            "precedents": [p["cell"] for p in precs],
            "precedent_sheets": sorted({p["sheet"] for p in precs}),
            "source": f"{spec['sheet']}!{spec['cell']}",
        }
    return {"error": f"unknown extract type {kind!r}"}


def check(answer: dict, expect: dict) -> tuple[bool, str]:
    if "error" in answer:
        return False, f"extraction error: {answer['error']}"
    match = expect["match"]
    tol = float(expect.get("tol", 0) or 0)

    if match in {"relative", "absolute"}:
        got = to_float(answer.get("value"))
        exp = float(expect["value"])
        if got is None:
            return False, f"non-numeric answer {answer.get('value')!r}"
        ok = abs(got - exp) <= (tol * max(1.0, abs(exp)) if match == "relative" else tol)
        return ok, f"{got} vs {exp} (±{tol}{'rel' if match=='relative' else ''})"

    if match == "bool":
        got = bool(answer.get("value"))
        ok = got == bool(expect["value"])
        return ok, f"{got} vs {expect['value']}"

    if match == "relative_map":  # unused alias
        match = "values"
    if match in {"values"}:
        exp = expect["values"]
        misses = []
        for k, ev in exp.items():
            gv = to_float(answer.get("values", {}).get(k))
            if gv is None or abs(gv - float(ev)) > tol * max(1.0, abs(float(ev))):
                misses.append(f"{k}:{answer.get('values',{}).get(k)}≠{ev}")
        return (not misses), ("all match" if not misses else "; ".join(misses))

    if match == "trace_precedent_sheet":
        ok = expect["precedent_sheet"] in answer.get("precedent_sheets", [])
        return ok, f"{answer.get('precedent_sheets')} contains {expect['precedent_sheet']}?"

    if match == "trace_formula":
        ok = answer.get("formula") == expect["formula"] and set(expect["precedents"]).issubset(set(answer.get("precedents", [])))
        return ok, f"formula {answer.get('formula')} / precedents {answer.get('precedents')}"

    if match == "formula_contains":
        f = answer.get("formula") or ""
        missing = [tok for tok in expect["contains"] if tok not in f]
        return (not missing), (f"formula {f}" if not missing else f"missing {missing} in {f}")

    return False, f"unknown match {match!r}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--workbook", required=True)
    args = ap.parse_args()

    suite = Path(args.suite)
    workbook = Path(args.workbook).resolve()
    checks = load_jsonl(suite / "checks.jsonl")

    tools = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[workbook.parent], cache_dir=suite / ".cache"))
    opened = tools.spreadsheet_open({"path": str(workbook)})
    if not opened["ok"]:
        raise SystemExit(f"open failed: {opened['error']['message']}")
    session = opened["session_id"]

    answers, results = [], []
    for spec in checks:
        answer = extract(tools, session, spec["extract"])
        ok, note = check(answer, spec["expect"])
        answers.append({"id": spec["id"], "answer": answer})
        results.append({"id": spec["id"], "verdict": "pass" if ok else "fail", "note": note,
                        "expect": {k: v for k, v in spec["expect"].items() if k != "match"}})

    passed = sum(1 for r in results if r["verdict"] == "pass")
    total = len(checks)

    # Stable output paths (overwritten) so re-runs are byte-identical.
    (suite / "checks_answers.json").write_text(json.dumps(answers, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    lines = [f"# Deterministic checks — {suite.name}", "", f"**Score: {passed}/{total}**  ·  workbook `{workbook.name}`  ·  no model in the loop", "",
             "| id | verdict | note |", "|----|---------|------|"]
    for r in results:
        mark = "✅" if r["verdict"] == "pass" else "❌"
        lines.append(f"| {r['id']} | {mark} | {r['note']} |")
    (suite / "checks_report.md").write_text("\n".join(lines) + "\n")

    print(f"{suite.name}: {passed}/{total} (deterministic)")
    for r in results:
        if r["verdict"] == "fail":
            print(f"  FAIL {r['id']}: {r['note']}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
