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


def test_is_installed_reflects_config(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    adapter = JsonFileAdapter(desc)
    assert adapter.is_installed() is False
    adapter.apply(_spec(), dry_run=False)
    assert adapter.is_installed() is True


def test_remove_deletes_entry_and_backs_up(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    adapter = JsonFileAdapter(desc)
    adapter.apply(_spec(), dry_run=False)
    result = adapter.remove(dry_run=False)
    assert result.ok and result.action == "removed"
    assert result.backup is not None
    assert adapter.is_installed() is False


def test_remove_absent_when_not_installed(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {}}))
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).remove(dry_run=False)
    assert result.action == "absent"


def test_remove_dry_run_writes_nothing(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    adapter = JsonFileAdapter(desc)
    adapter.apply(_spec(), dry_run=False)
    before = cfg.read_text()
    result = adapter.remove(dry_run=True)
    assert result.action == "dry-run"
    assert cfg.read_text() == before
