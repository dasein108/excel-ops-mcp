from __future__ import annotations

import argparse
import os
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools


def resolve_config(argv: list[str] | None = None, environ: dict | None = None) -> ExcelMcpConfig:
    """Build server config from CLI args and environment.

    Allowed roots come from ``--allowed-root`` (repeatable) and the
    ``EXCEL_MCP_ALLOWED_ROOTS`` env var (os.pathsep-separated). When neither is
    set, default to the user's HOME directory — a GUI host (e.g. Claude Desktop)
    launches the server with an unhelpful working directory (often ``/``), so
    ``Path.cwd()`` would block every real workbook.
    """
    environ = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(prog="excel-ops-mcp", add_help=False)
    parser.add_argument("--allowed-root", action="append", default=[], dest="allowed_roots")
    parser.add_argument("--cache-dir", default=None)
    args, _ = parser.parse_known_args(argv)

    roots: list[str] = list(args.allowed_roots)
    env_roots = environ.get("EXCEL_MCP_ALLOWED_ROOTS")
    if env_roots:
        roots.extend(p for p in env_roots.split(os.pathsep) if p)
    if not roots:
        roots = [str(Path.home())]

    kwargs: dict = {"allowed_roots": [Path(r) for r in roots]}
    cache_dir = args.cache_dir or environ.get("EXCEL_MCP_CACHE_DIR")
    if cache_dir:
        kwargs["cache_dir"] = Path(cache_dir)
    return ExcelMcpConfig(**kwargs)


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - depends on optional runtime install
        raise SystemExit("The 'mcp' package is required to run the MCP server.") from exc

    app = FastMCP("excel-mcp")
    tools = ExcelMcpTools(resolve_config())

    @app.tool()
    def spreadsheet_open(path: str) -> dict:
        return tools.spreadsheet_open({"path": path})

    @app.tool()
    def spreadsheet_describe(session_id: str, detail: str = "compact") -> dict:
        return tools.spreadsheet_describe({"session_id": session_id, "detail": detail})

    @app.tool()
    def spreadsheet_query(session_id: str, sql: str, limit: int | None = None) -> dict:
        return tools.spreadsheet_query({"session_id": session_id, "sql": sql, "limit": limit})

    @app.tool()
    def spreadsheet_read_range(session_id: str, sheet: str, range: str, include: list[str] | None = None) -> dict:
        return tools.spreadsheet_read_range({"session_id": session_id, "sheet": sheet, "range": range, "include": include or ["values"]})

    @app.tool()
    def spreadsheet_trace(session_id: str, sheet: str, cell: str, depth: int = 1) -> dict:
        return tools.spreadsheet_trace({"session_id": session_id, "sheet": sheet, "cell": cell, "depth": depth})

    @app.tool()
    def spreadsheet_write(session_id: str, operations: list[dict], dry_run: bool = True) -> dict:
        return tools.spreadsheet_write({"session_id": session_id, "operations": operations, "dry_run": dry_run})

    @app.tool()
    def spreadsheet_commit(session_id: str, staged_id: str, output_path: str | None = None, overwrite: bool = False) -> dict:
        return tools.spreadsheet_commit({"session_id": session_id, "staged_id": staged_id, "output_path": output_path, "overwrite": overwrite})

    @app.tool()
    def spreadsheet_diff(session_id: str, staged_id: str | None = None) -> dict:
        return tools.spreadsheet_diff({"session_id": session_id, "staged_id": staged_id})

    app.run()


if __name__ == "__main__":
    main()

