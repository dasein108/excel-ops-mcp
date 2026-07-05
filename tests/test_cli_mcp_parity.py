import json
from pathlib import Path

from excel_mcp.cli import main
from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())
ROOT = str(Path("examples").resolve())


def test_summary_parity_cli_vs_tool(tmp_path, capsys):
    main(["inspect", EXAMPLE, "--allowed-root", ROOT, "--mode", "summary", "--sheet", "Dashboard", "--range", "B5:F5"])
    cli_out = json.loads(capsys.readouterr().out)
    tool_out = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path(ROOT)], cache_dir=tmp_path)).spreadsheet_inspect(
        {"path": EXAMPLE, "mode": "summary", "sheet": "Dashboard", "range": "B5:F5"})
    assert round(cli_out["total"]) == round(tool_out["total"]) == 12784732
    assert round(cli_out["mean"]) == round(tool_out["mean"]) == 2556946
