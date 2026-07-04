import json

from excel_mcp.installer.adapters.json_file import JsonDescriptor, JsonFileAdapter
from excel_mcp.installer.spec import ServerSpec


def _spec():
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/abs/uvx")


def test_apply_writes_gui_absolute_command(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=False)
    assert result.ok and result.action == "added"
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["excel-ops-mcp"]["command"] == "/abs/uvx"


def test_dry_run_writes_nothing(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=True)
    assert result.action == "dry-run"
    assert not cfg.exists()


def test_apply_backs_up_existing(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"x": {"command": "z"}}}))
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=False)
    assert result.backup == str(tmp_path / "mcp.json.bak")
    assert (tmp_path / "mcp.json.bak").exists()


def test_malformed_config_returns_error_result(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{bad")
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=False)
    assert not result.ok
    assert result.action == "skipped"
    assert result.error


def test_detect_true_when_config_dir_exists(tmp_path):
    (tmp_path / ".cursor").mkdir()
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True,
                          path_fn=lambda: tmp_path / ".cursor" / "mcp.json",
                          detect_dirs=(tmp_path / ".cursor",))
    assert JsonFileAdapter(desc).detect() is True


def test_detect_false_when_nothing_present(tmp_path):
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True,
                          path_fn=lambda: tmp_path / ".cursor" / "mcp.json",
                          detect_dirs=(tmp_path / ".cursor",))
    assert JsonFileAdapter(desc).detect() is False
