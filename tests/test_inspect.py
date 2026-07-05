# tests/test_inspect.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path):
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))


def test_inspect_describe_by_path_auto_opens(tmp_path):
    resp = _tools(tmp_path).spreadsheet_inspect({"path": EXAMPLE, "mode": "describe"})
    assert resp["ok"]
    assert resp["session_id"]
    assert resp["best_source"]


def test_inspect_summary_reuses_session(tmp_path):
    tools = _tools(tmp_path)
    described = tools.spreadsheet_inspect({"path": EXAMPLE, "mode": "describe"})
    resp = tools.spreadsheet_inspect(
        {"session_id": described["session_id"], "mode": "summary", "sheet": "Dashboard", "range": "B5:F5", "growth": True}
    )
    assert round(resp["total"]) == 12784732
    assert [round(g, 1) for g in resp["yoy_growth_pct"]] == [68.8, 12.0, 8.0, 5.0]


def test_inspect_bad_mode(tmp_path):
    resp = _tools(tmp_path).spreadsheet_inspect({"path": EXAMPLE, "mode": "wat"})
    assert resp["ok"] is False
    assert resp["error"]["code"] == "invalid_mode"
