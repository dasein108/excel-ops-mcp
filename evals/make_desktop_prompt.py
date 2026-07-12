#!/usr/bin/env python3
"""Emit a copy-paste prompt to run a suite's questions in Claude Desktop.

Two modes let you A/B how Claude Desktop handles the same workbook:

  native  — upload the .xlsx into the chat; Claude answers with its own tools
            (analysis / code). Run: --mode native
  mcp      — Claude uses the excel-ops MCP; give it the workbook path.
            Run: --mode mcp --path /abs/path/to/saas.xlsx

Paste the emitted prompt into a fresh Claude Desktop chat (upload the file for
native mode). Claude returns a ```jsonl block; save it as answers.jsonl and score
with run_eval.py, or compare both modes with run_compare.py.

    python evals/make_desktop_prompt.py --suite evals/saas_v1 --mode native
    python evals/make_desktop_prompt.py --suite evals/saas_v1 --mode mcp --path "$PWD/examples/saas.xlsx"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, help="suite dir containing questions.jsonl")
    ap.add_argument("--mode", choices=["native", "mcp"], required=True)
    ap.add_argument("--path", help="workbook path Claude should open (mcp mode)")
    args = ap.parse_args()

    suite = Path(args.suite)
    questions = [json.loads(line) for line in (suite / "questions.jsonl").read_text().splitlines() if line.strip()]

    if args.mode == "native":
        access = (
            "The workbook is attached to this conversation as an .xlsx file. "
            "Use your own tools to read it. Do not use any MCP server."
        )
    else:
        path = args.path or "<ABSOLUTE PATH TO WORKBOOK>.xlsx"
        access = (
            f"Use ONLY the excel-ops MCP tools (spreadsheet_open, workbook_list, "
            f"spreadsheet_query, spreadsheet_read_range, spreadsheet_trace) to read "
            f"the workbook at:\n    {path}\n"
            "Do not upload or analyze the file any other way."
        )

    lines = [
        f"You are answering {len(questions)} questions about a spreadsheet model.",
        "",
        access,
        "",
        "Answer each question. Return ONLY a fenced ```jsonl code block, one JSON",
        'object per line: {"id": "<id>", "answer": <value>}. Use a bare number for',
        "numeric answers (no $ or commas), a short string otherwise. No prose outside",
        "the code block.",
        "",
        "Questions:",
    ]
    for q in questions:
        lines.append(f"- [{q['id']}] {q['question']}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
