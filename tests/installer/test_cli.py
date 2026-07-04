from excel_mcp.installer.cli import main


def test_version_flag_exits_zero(capsys):
    rc = main(["--version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "excel-ops-mcp-install" in out
