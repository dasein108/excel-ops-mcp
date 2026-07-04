from excel_mcp.installer.spec import ServerSpec, default_spec, resolve_uvx_path


def test_entry_uses_bare_uvx_for_cli_agents():
    spec = ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/opt/uv/bin/uvx")
    assert spec.entry(gui=False) == {"command": "uvx", "args": ["excel-ops-mcp"]}


def test_entry_uses_absolute_uvx_for_gui_agents():
    spec = ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/opt/uv/bin/uvx")
    assert spec.entry(gui=True) == {"command": "/opt/uv/bin/uvx", "args": ["excel-ops-mcp"]}


def test_default_spec_shape():
    spec = default_spec()
    assert spec.name == "excel-ops-mcp"
    assert spec.args == ("excel-ops-mcp",)


def test_resolve_uvx_falls_back_to_bare(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert resolve_uvx_path() == "uvx"
