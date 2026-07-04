import subprocess

from excel_mcp.installer.adapters import claude_code as cc
from excel_mcp.installer.adapters.claude_code import ClaudeCodeCliAdapter
from excel_mcp.installer.spec import ServerSpec


def _spec():
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/abs/uvx")


def test_apply_builds_correct_add_command(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().apply(_spec(), dry_run=False)
    assert result.ok and result.action == "added"
    add_cmd = calls[-1]
    assert add_cmd == ["claude", "mcp", "add", "--scope", "user",
                       "excel-ops-mcp", "--", "uvx", "excel-ops-mcp"]


def test_apply_reports_error_on_nonzero(monkeypatch):
    def fake_run(cmd, **kw):
        if cmd[2] == "remove":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().apply(_spec(), dry_run=False)
    assert not result.ok
    assert result.action == "skipped"
    assert "boom" in (result.error or "")


def test_dry_run_shows_command_and_runs_nothing(monkeypatch):
    def fake_run(cmd, **kw):
        raise AssertionError("should not run in dry-run")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().apply(_spec(), dry_run=True)
    assert result.action == "dry-run"
    assert "claude mcp add" in (result.note or "")


def test_detect_uses_which(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda n: "/usr/bin/claude" if n == "claude" else None)
    assert ClaudeCodeCliAdapter().detect() is True
    monkeypatch.setattr(cc.shutil, "which", lambda n: None)
    assert ClaudeCodeCliAdapter().detect() is False


def test_is_installed_uses_mcp_get(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda n: "/usr/bin/claude")

    def fake_run(cmd, **kw):
        rc = 0 if cmd[:3] == ["claude", "mcp", "get"] else 1
        return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")

    monkeypatch.setattr(cc, "_run", fake_run)
    assert ClaudeCodeCliAdapter().is_installed() is True


def test_is_installed_false_when_claude_missing(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda n: None)
    assert ClaudeCodeCliAdapter().is_installed() is False


def test_remove_builds_command(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().remove(dry_run=False)
    assert result.ok and result.action == "removed"
    assert calls[-1] == ["claude", "mcp", "remove", "--scope", "user", "excel-ops-mcp"]


def test_remove_absent_on_nonzero(monkeypatch):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no such server")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().remove(dry_run=False)
    assert result.ok and result.action == "absent"
