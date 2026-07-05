import json
from pathlib import Path

from excel_mcp.cli import main

EXAMPLE = str(Path("examples/saas.xlsx").resolve())
ROOT = str(Path("examples").resolve())


def test_cli_inspect_summary(capsys):
    code = main(["inspect", EXAMPLE, "--allowed-root", ROOT, "--mode", "summary",
                 "--sheet", "Dashboard", "--range", "B5:F5", "--growth"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert round(out["total"]) == 12784732


def test_cli_edit_commit(tmp_path, capsys):
    ops = json.dumps([{"type": "set_values", "sheet": "Dashboard", "start": "A20", "values": [["hi"]]}])
    out_path = str(tmp_path / "cli_out.xlsx")
    code = main(["edit", EXAMPLE, "--allowed-root", ROOT, "--allowed-root", str(tmp_path),
                 "--ops", ops, "--commit", "--output", out_path])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert Path(out_path).exists()
    assert payload["output_path"] == out_path
