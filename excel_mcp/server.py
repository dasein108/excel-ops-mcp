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
    def spreadsheet_open(path: str | None = None, content_base64: str | None = None, filename: str | None = None) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list] Open an .xlsx workbook and return a session_id used by the other tools.

        Paths resolve against the SERVER HOST filesystem, relative to the
        server's allowed roots (see workbook_list for those roots). Absolute
        paths are safest. If open fails, the error 'details' report the roots
        searched and 'did_you_mean' near-matches — use them to correct the path
        in one retry instead of guessing.

        If the caller does NOT share the server's filesystem (e.g. a file
        uploaded into a sandbox), skip 'path' and pass the raw bytes as
        'content_base64' plus a 'filename' ending in .xlsx.
        """
        return tools.spreadsheet_open({"path": path, "content_base64": content_base64, "filename": filename})

    @app.tool()
    def spreadsheet_inspect(mode: str = "describe", path: str | None = None, session_id: str | None = None,
                            content_base64: str | None = None, filename: str | None = None,
                            sheet: str | None = None, range: str | None = None, cell: str | None = None,
                            depth: int = 1, include: list[str] | None = None, detail: str = "compact",
                            growth: bool = False) -> dict:
        """Inspect a workbook. Pass a 'path' (auto-opens) OR a 'session_id' from a prior call.

        mode='describe' -> sheets + a 'best_source' hint ranking the cleanest sheet first.
        mode='summary'  -> server computes total/mean/min/max (+ yoy_growth_pct when growth=true)
                           over sheet+range, so you never sum cells yourself.
        mode='read'     -> raw cells for sheet+range (include=['values','formulas',...]).
        mode='trace'    -> formula precedents for sheet+cell to 'depth' levels.
        """
        return tools.spreadsheet_inspect({"mode": mode, "path": path, "session_id": session_id,
            "content_base64": content_base64, "filename": filename, "sheet": sheet, "range": range,
            "cell": cell, "depth": depth, "include": include, "detail": detail, "growth": growth})

    @app.tool()
    def workbook_list(glob: str | None = None, limit: int = 200) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list] List .xlsx workbooks under the server's allowed roots.

        Call this first when you don't know where files live: it returns the
        allowed 'root_paths' and matching 'workbooks' (path/size/modified), so
        the next spreadsheet_open succeeds on the first try. 'glob' filters on
        an fnmatch pattern (e.g. '*.xlsx', 'reports/*.xlsx').
        """
        return tools.workbook_list({"glob": glob, "limit": limit})

    @app.tool()
    def spreadsheet_describe(session_id: str, detail: str = "compact") -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list]"""
        return tools.spreadsheet_describe({"session_id": session_id, "detail": detail})

    @app.tool()
    def spreadsheet_query(sql: str, path: str | None = None, session_id: str | None = None,
                          limit: int | None = None, content_base64: str | None = None, filename: str | None = None) -> dict:
        """Run a read-only SQL query over a workbook. Pass 'path' (auto-opens) OR 'session_id'."""
        return tools.spreadsheet_query({"path": path, "session_id": session_id, "sql": sql, "limit": limit,
            "content_base64": content_base64, "filename": filename})

    @app.tool()
    def spreadsheet_list(glob: str | None = None, limit: int = 200) -> dict:
        """List .xlsx workbooks under the server's allowed roots."""
        return tools.spreadsheet_list({"glob": glob, "limit": limit})

    @app.tool()
    def spreadsheet_read_range(session_id: str, sheet: str, range: str, include: list[str] | None = None) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list]"""
        return tools.spreadsheet_read_range({"session_id": session_id, "sheet": sheet, "range": range, "include": include or ["values"]})

    @app.tool()
    def spreadsheet_trace(session_id: str, sheet: str, cell: str, depth: int = 1) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list]"""
        return tools.spreadsheet_trace({"session_id": session_id, "sheet": sheet, "cell": cell, "depth": depth})

    @app.tool()
    def spreadsheet_write(session_id: str, operations: list[dict], dry_run: bool = True) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list] Stage cell edits (dry_run=True previews; commit them with spreadsheet_commit).

        Each operation is {"type", "sheet", ...}. Supported types and their fields:
          - set_values:  {"type":"set_values","sheet":"Sheet1","start":"A1","values":[[1,2],[3,4]]}
                         'start' is the top-left cell; 'values' is a row-major 2D array.
          - set_formula: {"type":"set_formula","sheet":"Sheet1","cell":"C2","formula":"=A2*B2"}
          - clear_range: {"type":"clear_range","sheet":"Sheet1","range":"A1:B10"}
          - append_rows: {"type":"append_rows","sheet":"Sheet1","rows":[["x",1],["y",2]]}
          - insert_rows: {"type":"insert_rows","sheet":"Sheet1","idx":5,"amount":1}
          - delete_rows: {"type":"delete_rows","sheet":"Sheet1","idx":5,"amount":1}
          - copy_range:  {"type":"copy_range","sheet":"Sheet1","source":"A1:B2","target":"D1"}
        Rejected operations come back in 'rejected_operations' with a per-op code and message.
        """
        return tools.spreadsheet_write({"session_id": session_id, "operations": operations, "dry_run": dry_run})

    @app.tool()
    def spreadsheet_commit(session_id: str, staged_id: str, output_path: str | None = None, overwrite: bool = False) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list]"""
        return tools.spreadsheet_commit({"session_id": session_id, "staged_id": staged_id, "output_path": output_path, "overwrite": overwrite})

    @app.tool()
    def spreadsheet_diff(session_id: str, staged_id: str | None = None) -> dict:
        """[DEPRECATED — use spreadsheet_inspect/edit/list]"""
        return tools.spreadsheet_diff({"session_id": session_id, "staged_id": staged_id})

    @app.tool()
    def spreadsheet_edit(operations: list[dict], path: str | None = None, session_id: str | None = None,
                         content_base64: str | None = None, filename: str | None = None,
                         dry_run: bool = False, commit: bool = True,
                         output_path: str | None = None, overwrite: bool = False) -> dict:
        """Apply cell edits in one call. Pass 'path' (auto-opens) OR 'session_id'.

        dry_run=true previews (stages, returns diff, writes nothing).
        dry_run=false + commit=true stages AND commits in a single call, returning
        'output_path' and 'changes'. Rejected operations abort the commit.
        Operation shapes are the same as the old spreadsheet_write (set_values,
        set_formula, clear_range, append_rows, insert_rows, delete_rows, copy_range).
        """
        return tools.spreadsheet_edit({"operations": operations, "path": path, "session_id": session_id,
            "content_base64": content_base64, "filename": filename, "dry_run": dry_run, "commit": commit,
            "output_path": output_path, "overwrite": overwrite})

    app.run()


if __name__ == "__main__":
    main()

