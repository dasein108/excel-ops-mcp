import json

import pytest

from excel_mcp.installer.errors import MalformedConfig
from excel_mcp.installer.merge import backup_file, json_upsert_server


def test_creates_file_when_absent(tmp_path):
    cfg = tmp_path / "sub" / "mcp.json"
    action = json_upsert_server(cfg, "mcpServers", "excel-ops-mcp",
                                {"command": "uvx", "args": ["excel-ops-mcp"]})
    assert action == "added"
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["excel-ops-mcp"] == {"command": "uvx", "args": ["excel-ops-mcp"]}


def test_preserves_existing_servers_and_keys(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}))
    json_upsert_server(cfg, "mcpServers", "excel-ops-mcp",
                       {"command": "uvx", "args": ["excel-ops-mcp"]})
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["other"] == {"command": "x"}
    assert data["theme"] == "dark"
    assert "excel-ops-mcp" in data["mcpServers"]


def test_updates_existing_entry_idempotent(tmp_path):
    cfg = tmp_path / "mcp.json"
    entry = {"command": "uvx", "args": ["excel-ops-mcp"]}
    assert json_upsert_server(cfg, "mcpServers", "excel-ops-mcp", entry) == "added"
    assert json_upsert_server(cfg, "mcpServers", "excel-ops-mcp", entry) == "updated"
    data = json.loads(cfg.read_text())
    assert list(data["mcpServers"].keys()) == ["excel-ops-mcp"]  # no duplicate


def test_malformed_json_raises_and_does_not_overwrite(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{ this is not json")
    with pytest.raises(MalformedConfig):
        json_upsert_server(cfg, "mcpServers", "excel-ops-mcp", {"command": "uvx", "args": []})
    assert cfg.read_text() == "{ this is not json"  # untouched


def test_backup_copies_existing(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("hello")
    bak = backup_file(cfg)
    assert bak == tmp_path / "mcp.json.bak"
    assert bak.read_text() == "hello"


def test_backup_none_when_absent(tmp_path):
    assert backup_file(tmp_path / "nope.json") is None
