import tomllib

from excel_mcp.installer.adapters.toml_file import TomlDescriptor, TomlFileAdapter
from excel_mcp.installer.spec import ServerSpec


def _spec():
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/abs/uvx")


def test_apply_writes_bare_uvx_for_cli_agent(tmp_path):
    cfg = tmp_path / "config.toml"
    desc = TomlDescriptor(key="codex", label="Codex", path_fn=lambda: cfg)
    result = TomlFileAdapter(desc).apply(_spec(), dry_run=False)
    assert result.ok and result.action == "added"
    data = tomllib.loads(cfg.read_text())
    assert data["mcp_servers"]["excel-ops-mcp"]["command"] == "uvx"


def test_dry_run_writes_nothing(tmp_path):
    cfg = tmp_path / "config.toml"
    desc = TomlDescriptor(key="codex", label="Codex", path_fn=lambda: cfg)
    result = TomlFileAdapter(desc).apply(_spec(), dry_run=True)
    assert result.action == "dry-run"
    assert not cfg.exists()


def test_detect_via_cli_on_path(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/codex" if n == "codex" else None)
    desc = TomlDescriptor(key="codex", label="Codex", path_fn=lambda: tmp_path / "c.toml",
                          cli_name="codex")
    assert TomlFileAdapter(desc).detect() is True
