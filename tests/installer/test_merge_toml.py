import tomllib

import pytest

from excel_mcp.installer.errors import MalformedConfig
from excel_mcp.installer.merge import (
    toml_has_server,
    toml_remove_server,
    toml_upsert_server,
)


def test_creates_toml_when_absent(tmp_path):
    cfg = tmp_path / "config.toml"
    action = toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    assert action == "added"
    data = tomllib.loads(cfg.read_text())
    assert data["mcp_servers"]["excel-ops-mcp"] == {"command": "uvx", "args": ["excel-ops-mcp"]}


def test_preserves_other_tables(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('model = "gpt-5"\n\n[mcp_servers.other]\ncommand = "x"\nargs = []\n')
    toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    data = tomllib.loads(cfg.read_text())
    assert data["model"] == "gpt-5"
    assert data["mcp_servers"]["other"]["command"] == "x"
    assert data["mcp_servers"]["excel-ops-mcp"]["command"] == "uvx"


def test_idempotent_update(tmp_path):
    cfg = tmp_path / "config.toml"
    assert toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"]) == "added"
    assert toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"]) == "updated"
    data = tomllib.loads(cfg.read_text())
    assert list(data["mcp_servers"].keys()) == ["excel-ops-mcp"]


def test_malformed_toml_raises_and_preserves(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("this = = broken")
    with pytest.raises(MalformedConfig):
        toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    assert cfg.read_text() == "this = = broken"


def test_toml_has_and_remove(tmp_path):
    cfg = tmp_path / "config.toml"
    assert toml_has_server(cfg, "excel-ops-mcp") is False
    toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    assert toml_has_server(cfg, "excel-ops-mcp") is True
    assert toml_remove_server(cfg, "excel-ops-mcp") == "removed"
    assert toml_has_server(cfg, "excel-ops-mcp") is False
    assert toml_remove_server(cfg, "excel-ops-mcp") == "absent"


def test_toml_remove_preserves_other_servers(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[mcp_servers.other]\ncommand = "x"\nargs = []\n')
    toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    assert toml_remove_server(cfg, "excel-ops-mcp") == "removed"
    data = tomllib.loads(cfg.read_text())
    assert "excel-ops-mcp" not in data["mcp_servers"]
    assert data["mcp_servers"]["other"]["command"] == "x"
