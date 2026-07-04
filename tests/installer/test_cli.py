import json

from excel_mcp.installer import tui
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


def test_agents_flag_installs_only_selected(fake_home, capsys):
    rc = main(["--agents", "cursor"])
    assert rc == 0
    cfg = fake_home / ".cursor" / "mcp.json"
    assert cfg.exists()
    data = json.loads(cfg.read_text())
    assert "excel-ops-mcp" in data["mcpServers"]
    # gemini NOT touched
    assert not (fake_home / ".gemini" / "settings.json").exists()


def test_dry_run_writes_nothing(fake_home):
    rc = main(["--agents", "cursor", "--dry-run"])
    assert rc == 0
    assert not (fake_home / ".cursor" / "mcp.json").exists()


def test_unknown_agent_key_errors(capsys):
    rc = main(["--agents", "bogus"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "bogus" in err


def test_uninstall_flag_removes(fake_home, capsys):
    main(["--agents", "cursor"])  # install first
    cfg = fake_home / ".cursor" / "mcp.json"
    assert "excel-ops-mcp" in json.loads(cfg.read_text())["mcpServers"]
    rc = main(["--uninstall", "cursor"])
    assert rc == 0
    assert "excel-ops-mcp" not in json.loads(cfg.read_text())["mcpServers"]


def test_interactive_install_mode_installs_checked(fake_home, monkeypatch):
    cursor_cfg = fake_home / ".cursor" / "mcp.json"
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(tui, "run_interactive",
                        lambda adapters, detected, installed: ("install", ["cursor"]))
    rc = main([])
    assert rc == 0
    assert "excel-ops-mcp" in json.loads(cursor_cfg.read_text())["mcpServers"]


def test_interactive_uninstall_mode_removes_checked(fake_home, monkeypatch):
    main(["--agents", "windsurf"])  # install first
    windsurf_cfg = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
    assert "excel-ops-mcp" in json.loads(windsurf_cfg.read_text())["mcpServers"]

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(tui, "run_interactive",
                        lambda adapters, detected, installed: ("uninstall", ["windsurf"]))
    rc = main([])
    assert rc == 0
    assert "excel-ops-mcp" not in json.loads(windsurf_cfg.read_text())["mcpServers"]


def test_non_interactive_without_flags_does_nothing(fake_home, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No terminal" in out
    assert not (fake_home / ".cursor" / "mcp.json").exists()
