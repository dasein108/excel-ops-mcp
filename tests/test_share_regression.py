from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def test_share_a_job_in_three_calls(tmp_path):
    tools = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[tmp_path, Path("examples").resolve()], cache_dir=tmp_path))
    # 1) describe -> pick best source
    d = tools.spreadsheet_inspect({"path": EXAMPLE, "mode": "describe"})
    sid = d["session_id"]
    assert d["best_source"][0]["sheet"] in {"Dashboard", "Revenue Model"}
    # 2) summary -> server math
    s = tools.spreadsheet_inspect({"session_id": sid, "mode": "summary", "sheet": "Dashboard", "range": "B5:F5", "growth": True})
    assert round(s["total"]) == 12784732 and round(s["max"]) == 3127445
    # 3) edit+commit -> add growth row in one call
    out = str(tmp_path / "saas.updated.xlsx")
    e = tools.spreadsheet_edit({"session_id": sid, "dry_run": False, "commit": True, "output_path": out,
        "operations": [{"type": "set_values", "sheet": "Dashboard", "start": "B13",
                        "values": [[0.688, 0.12, 0.08, 0.05]]}]})
    assert e["ok"] and Path(out).exists()
