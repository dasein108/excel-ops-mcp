from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from pydantic import ValidationError

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.normalizers import derived_percent_column_names, is_percent_like_column
from excel_mcp.tools import ExcelMcpTools


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        response = dispatch(args)
    except ValidationError as exc:
        response = _error("invalid_arguments", str(exc))
    except Exception as exc:
        response = _error("cli_failed", str(exc))

    _print_json(response, pretty=args.pretty)
    return 0 if response.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--allowed-root", action="append", default=None, help="Allowed filesystem root. Repeatable.")
    parent.add_argument("--cache-dir", default=None, help="Session/cache directory.")
    parent.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parent.add_argument("--output-profile", choices=["compact", "verbose"], default="compact", help="Reserved output profile flag.")

    parser = argparse.ArgumentParser(prog="excel-ops", description="Excel operations CLI backed by excel_mcp.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    open_parser = subparsers.add_parser("open", parents=[parent], help="Open an Excel workbook and return a session.")
    open_parser.add_argument("path")

    sheets = subparsers.add_parser("sheets", parents=[parent], help="List workbook sheets by path or session.")
    sheets.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    sheets.add_argument("--session", dest="session_id", help="Existing session id.")

    tables = subparsers.add_parser("tables", parents=[parent], help="List detected SQL tables/regions by path or session.")
    tables.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    tables.add_argument("--session", dest="session_id", help="Existing session id.")
    tables.add_argument("--sheet", default=None, help="Filter to one sheet.")

    describe = subparsers.add_parser("describe", parents=[parent], help="Describe a workbook by path or session.")
    describe.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    describe.add_argument("--session", dest="session_id", help="Existing session id.")
    describe.add_argument("--detail", choices=["compact", "standard"], default="compact")

    query = subparsers.add_parser("query", parents=[parent], help="Run read-only SQL by path or session.")
    query.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    query.add_argument("--session", dest="session_id", help="Existing session id.")
    query.add_argument("--sql", required=True)
    query.add_argument("--limit", type=int, default=None)

    read_range = subparsers.add_parser("read-range", parents=[parent], help="Read a bounded range by path or session.")
    read_range.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    read_range.add_argument("--session", dest="session_id", help="Existing session id.")
    read_range.add_argument("--sheet", required=True)
    read_range.add_argument("--range", required=True)
    read_range.add_argument("--include", action="append", default=None, help="Field to include. Repeatable.")

    trace = subparsers.add_parser("trace", parents=[parent], help="Trace a cell's formula lineage (precedents).")
    trace.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    trace.add_argument("--session", dest="session_id", help="Existing session id.")
    trace.add_argument("--sheet", required=True)
    trace.add_argument("--cell", required=True, help="Target cell, e.g. B5.")
    trace.add_argument("--depth", type=int, default=1, help="Levels of precedents to expand (0-5).")

    write = subparsers.add_parser("write", parents=[parent], help="Stage write operations.")
    write.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    write.add_argument("--session", dest="session_id", help="Existing session id.")
    write.add_argument("--ops", required=True, help="JSON operations array or path to JSON file.")
    write.add_argument("--apply", action="store_true", help="Reserved; writes are staged and never committed by this command.")

    diff = subparsers.add_parser("diff", parents=[parent], help="Show a staged diff.")
    diff.add_argument("--session", dest="session_id", required=True)
    diff.add_argument("--staged", dest="staged_id", default=None)

    commit = subparsers.add_parser("commit", parents=[parent], help="Commit staged changes to an output workbook.")
    commit.add_argument("--session", dest="session_id", required=True)
    commit.add_argument("--staged", dest="staged_id", required=True)
    commit.add_argument("--output", dest="output_path", default=None)
    commit.add_argument("--overwrite", action="store_true")

    audit = subparsers.add_parser("audit", parents=[parent], help="List audit events.")
    audit.add_argument("--session", dest="session_id", default=None)
    audit.add_argument("--path", dest="path", default=None)
    audit.add_argument("--limit", type=int, default=100)

    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    tools = ExcelMcpTools(_config(args))
    if args.command == "open":
        return tools.spreadsheet_open({"path": args.path})

    if args.command == "sheets":
        session_id = _session_or_open(tools, args)
        described = tools.spreadsheet_describe({"session_id": session_id, "detail": "compact"})
        if not described.get("ok"):
            return described
        response = {
            "ok": True,
            "session_id": session_id,
            "sheet_count": described["sheet_count"],
            "sheets": [
                {
                    "name": sheet["name"],
                    "bounds": sheet["bounds"],
                    "hidden": sheet["hidden"],
                    "formula_count": sheet["formula_count"],
                    "region_count": len(sheet["regions"]),
                }
                for sheet in described["sheets"]
            ],
        }
        tools.record_cli_audit("sheets", response, {"target": getattr(args, "target", None)}, None)
        return response

    if args.command == "tables":
        session_id = _session_or_open(tools, args)
        described = tools.spreadsheet_describe({"session_id": session_id, "detail": "compact"})
        if not described.get("ok"):
            return described
        rows = []
        for sheet in described["sheets"]:
            if args.sheet and sheet["name"] != args.sheet:
                continue
            for region in sheet["regions"]:
                columns = [column["name"] for column in region["columns"]]
                rows.append(
                    {
                        "sheet": sheet["name"],
                        "table_name": region["table_name"],
                        "bounds": region["bounds"],
                        "kind": region["region_kind"],
                        "orientation": region.get("orientation", "tabular"),
                        "rows": region["row_count"],
                        "columns": columns,
                        "derived_columns": _derived_columns_for_region(region),
                    }
                )
        response = {"ok": True, "session_id": session_id, "table_count": len(rows), "tables": rows}
        tools.record_cli_audit("tables", response, {"target": getattr(args, "target", None), "sheet": args.sheet}, None)
        return response

    if args.command == "describe":
        session_id = _session_or_open(tools, args)
        return tools.spreadsheet_describe({"session_id": session_id, "detail": args.detail})

    if args.command == "query":
        session_id = _session_or_open(tools, args)
        return tools.spreadsheet_query({"session_id": session_id, "sql": args.sql, "limit": args.limit})

    if args.command == "read-range":
        session_id = _session_or_open(tools, args)
        return tools.spreadsheet_read_range(
            {
                "session_id": session_id,
                "sheet": args.sheet,
                "range": args.range,
                "include": args.include or ["values"],
            }
        )

    if args.command == "trace":
        session_id = _session_or_open(tools, args)
        return tools.spreadsheet_trace(
            {"session_id": session_id, "sheet": args.sheet, "cell": args.cell, "depth": args.depth}
        )

    if args.command == "write":
        session_id = _session_or_open(tools, args)
        return tools.spreadsheet_write({"session_id": session_id, "operations": _load_ops(args.ops), "dry_run": True})

    if args.command == "diff":
        return tools.spreadsheet_diff({"session_id": args.session_id, "staged_id": args.staged_id})

    if args.command == "commit":
        return tools.spreadsheet_commit(
            {
                "session_id": args.session_id,
                "staged_id": args.staged_id,
                "output_path": args.output_path,
                "overwrite": args.overwrite,
            }
        )

    if args.command == "audit":
        return tools.audit_events(session_id=args.session_id, path=args.path, limit=args.limit)

    return _error("unknown_command", args.command)


def _config(args: argparse.Namespace) -> ExcelMcpConfig:
    allowed_roots = [Path(item) for item in (args.allowed_root or [Path.cwd()])]
    cache_dir = Path(args.cache_dir) if args.cache_dir else Path.cwd() / ".excel-ops-cache"
    return ExcelMcpConfig(allowed_roots=allowed_roots, cache_dir=cache_dir)


def _session_or_open(tools: ExcelMcpTools, args: argparse.Namespace) -> str:
    if getattr(args, "session_id", None):
        return args.session_id
    target = getattr(args, "target", None)
    if not target:
        raise ValueError("Provide a workbook path or --session.")
    opened = tools.spreadsheet_open({"path": target})
    if not opened.get("ok"):
        raise ValueError(opened.get("error", {}).get("message", "Failed to open workbook."))
    return opened["session_id"]


def _load_ops(value: str) -> list[dict[str, Any]]:
    path = Path(value)
    text = path.read_text(encoding="utf-8") if path.exists() else value
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("--ops must be a JSON array of operation objects.")
    if not all(isinstance(item, dict) for item in parsed):
        raise ValueError("--ops must be a JSON array of operation objects.")
    return parsed


def _print_json(response: dict[str, Any], pretty: bool = False) -> None:
    indent = 2 if pretty else None
    print(json.dumps(response, ensure_ascii=False, indent=indent, default=str))


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "details": {}}}


def _derived_columns_for_region(region: dict[str, Any]) -> list[str]:
    derived: list[str] = []
    samples = region.get("sample_rows") or []
    for column in region.get("columns", []):
        name = column["name"]
        values = [row.get(name) for row in samples if isinstance(row, dict)]
        if is_percent_like_column(name, values):
            derived.extend(derived_percent_column_names(name))
    return derived


if __name__ == "__main__":
    raise SystemExit(main())
