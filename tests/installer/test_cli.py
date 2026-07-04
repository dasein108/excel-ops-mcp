import json

from excel_mcp.installer.cli import main


def test_version_flag_exits_zero(capsys):
    rc = main(["--version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "excel-ops-mcp-install" in out


def test_list_prints_agents(capsys):
    rc = main(["--list"])
    out = capsys.readouterr().out
    assert rc == 0
    for label in ["Claude Desktop", "Claude Code", "Codex", "Gemini CLI", "Cursor", "Windsurf"]:
        assert label in out


def test_agents_flag_applies_only_selected(fake_home, capsys):
    rc = main(["--agents", "cursor", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0
    cfg = fake_home / ".cursor" / "mcp.json"
    assert cfg.exists()
    data = json.loads(cfg.read_text())
    assert "excel-ops-mcp" in data["mcpServers"]
    # gemini NOT touched
    assert not (fake_home / ".gemini" / "settings.json").exists()


def test_dry_run_writes_nothing(fake_home, capsys):
    rc = main(["--agents", "cursor", "--dry-run"])
    assert rc == 0
    assert not (fake_home / ".cursor" / "mcp.json").exists()


def test_unknown_agent_key_errors(capsys):
    rc = main(["--agents", "bogus", "--yes"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "bogus" in err
