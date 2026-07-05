import base64

import openpyxl
import pytest

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools


@pytest.fixture()
def workbook_root(tmp_path):
    wb = openpyxl.Workbook()
    wb.active["A1"] = "hello"
    path = tmp_path / "Financial_Report.xlsx"
    wb.save(path)
    return tmp_path, path


@pytest.fixture()
def tools(workbook_root):
    root, _ = workbook_root
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[root], cache_dir=root / ".cache"))


def test_file_not_found_reports_search_roots_and_did_you_mean(tools, workbook_root):
    root, _ = workbook_root
    response = tools.spreadsheet_open({"path": str(root / "Financial_Reporx.xlsx")})
    assert response["ok"] is False
    details = response["error"]["details"]
    assert str(root) in details["search_roots"]
    assert any("Financial_Report.xlsx" in match for match in details["did_you_mean"])


def test_path_not_allowed_still_teaches_roots(tools, tmp_path):
    outside = tmp_path.parent / "elsewhere.xlsx"
    response = tools.spreadsheet_open({"path": str(outside)})
    assert response["error"]["code"] == "path_not_allowed"
    assert "search_roots" in response["error"]["details"]


def test_workbook_list_returns_workbooks_under_roots(tools, workbook_root):
    root, path = workbook_root
    response = tools.workbook_list({})
    assert response["ok"] is True
    assert str(root) in response["root_paths"]
    assert str(path) in [wb["path"] for wb in response["workbooks"]]


def test_workbook_list_glob_filters(tools):
    assert tools.workbook_list({"glob": "*.csv"})["workbooks"] == []
    assert tools.workbook_list({"glob": "*.xlsx"})["workbooks"]


def test_open_accepts_base64_content(tools, workbook_root):
    _, path = workbook_root
    content = base64.b64encode(path.read_bytes()).decode()
    response = tools.spreadsheet_open({"content_base64": content, "filename": "uploaded.xlsx"})
    assert response["ok"] is True
    assert response["session_id"]


def test_open_rejects_bad_base64(tools):
    response = tools.spreadsheet_open({"content_base64": "not base64!!", "filename": "x.xlsx"})
    assert response["error"]["code"] == "invalid_content"


def test_open_rejects_non_xlsx_upload(tools):
    content = base64.b64encode(b"anything").decode()
    response = tools.spreadsheet_open({"content_base64": content, "filename": "x.csv"})
    assert response["error"]["code"] == "unsupported_extension"


def test_open_without_source_errors(tools):
    assert tools.spreadsheet_open({})["error"]["code"] == "missing_source"
