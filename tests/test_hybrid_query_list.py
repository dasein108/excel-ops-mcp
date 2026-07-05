from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path):
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))


def test_query_by_path_auto_opens(tmp_path):
    resp = _tools(tmp_path).spreadsheet_query({"path": EXAMPLE, "sql": "select 1 as one"})
    assert resp["ok"]
    assert resp["rows"][0]["one"] == 1


def test_spreadsheet_list_matches_workbook_list(tmp_path):
    tools = _tools(tmp_path)
    assert tools.spreadsheet_list({"glob": "*.xlsx"})["ok"]
