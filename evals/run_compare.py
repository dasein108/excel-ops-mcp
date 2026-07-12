#!/usr/bin/env python3
"""Score two answer sets against the same gold and print a side-by-side report.

Built for A/B: Claude Desktop reading a workbook natively vs. via the excel-ops
MCP. Reuses run_eval's tolerant judge, so scoring matches the single-run reports.

    python evals/run_compare.py --suite evals/saas_v1 \
        --a runs/native/answers.jsonl --label-a native \
        --b runs/mcp/answers.jsonl    --label-b mcp \
        --out evals/saas_v1/compare_native_vs_mcp.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import judge, load_jsonl  # noqa: E402  (reuse the canonical scorer)

_MARK = {True: "✅", False: "❌", None: "⚠️"}


def _trim(value, width: int = 22) -> str:
    text = str(value)
    return text if len(text) <= width else text[: width - 3] + "..."


def _score(gold_rows: dict, answers_path: Path) -> dict:
    answers = {row["id"]: row for row in load_jsonl(answers_path)}
    scored = {}
    for qid, gold in gold_rows.items():
        ans = answers.get(qid)
        if ans is None:
            scored[qid] = (None, "no answer", None)
        else:
            ok, reason = judge(gold, ans.get("answer"))
            scored[qid] = (ok, reason, ans.get("answer"))
    return scored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--b", required=True)
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--out", help="write the markdown report here too")
    args = ap.parse_args()

    suite = Path(args.suite)
    gold = {row["id"]: row for row in load_jsonl(suite / "gold.jsonl")}
    a = _score(gold, Path(args.a))
    b = _score(gold, Path(args.b))
    la, lb = args.label_a, args.label_b

    lines = [
        f"# A/B eval — {suite.name}",
        "",
        f"**{la}** (`{args.a}`) vs **{lb}** (`{args.b}`)",
        "",
        f"| id | {la} | {lb} | expected | {la} got | {lb} got |",
        "|----|------|------|----------|---------|---------|",
    ]
    a_pass = b_pass = 0
    only_a, only_b, both_fail = [], [], []
    for qid, g in gold.items():
        av, _, ag = a[qid]
        bv, _, bg = b[qid]
        a_pass += 1 if av else 0
        b_pass += 1 if bv else 0
        if av and not bv:
            only_a.append(qid)
        elif bv and not av:
            only_b.append(qid)
        elif not av and not bv:
            both_fail.append(qid)
        lines.append(
            f"| {qid} | {_MARK[av]} | {_MARK[bv]} | {_trim(g.get('expected'))} "
            f"| {_trim(ag)} | {_trim(bg)} |"
        )

    n = len(gold)
    lines += [
        "",
        f"**{la}: {a_pass}/{n}**  ·  **{lb}: {b_pass}/{n}**  ·  "
        f"delta {b_pass - a_pass:+d} ({lb} − {la})",
    ]
    if only_a:
        lines.append(f"- {la} right / {lb} wrong: {', '.join(only_a)}")
    if only_b:
        lines.append(f"- {lb} right / {la} wrong: {', '.join(only_b)}")
    if both_fail:
        lines.append(f"- both wrong: {', '.join(both_fail)}")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
