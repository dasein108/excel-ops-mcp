# tests/test_edit.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path):
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[tmp_path, Path("examples").resolve()], cache_dir=tmp_path))


def _ops():
    return [{"type": "set_values", "sheet": "Dashboard", "start": "A20", "values": [["hello"]]}]


def test_edit_dry_run_stages_without_commit(tmp_path):
    resp = _tools(tmp_path).spreadsheet_edit({"path": EXAMPLE, "operations": _ops(), "dry_run": True})
    assert resp["ok"]
    assert resp["staged_id"]
    assert "output_path" not in resp or resp.get("output_path") is None


def test_edit_commit_writes_file_in_one_call(tmp_path):
    out = str(tmp_path / "out.xlsx")
    resp = _tools(tmp_path).spreadsheet_edit(
        {"path": EXAMPLE, "operations": _ops(), "dry_run": False, "commit": True, "output_path": out})
    assert resp["ok"]
    assert resp["output_path"] == out
    assert Path(out).exists()


def test_edit_rejected_ops_do_not_commit(tmp_path):
    bad = [{"type": "bogus_op", "sheet": "Dashboard"}]
    resp = _tools(tmp_path).spreadsheet_edit(
        {"path": EXAMPLE, "operations": bad, "dry_run": False, "commit": True, "output_path": str(tmp_path / "x.xlsx")})
    assert resp["rejected_operations"]
    assert not Path(tmp_path / "x.xlsx").exists()
