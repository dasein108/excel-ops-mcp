from excel_mcp.installer.registry import adapter_by_key, build_registry


def test_registry_has_six_expected_agents():
    keys = [a.key for a in build_registry()]
    assert keys == ["claude-desktop", "claude-code", "codex", "gemini", "cursor", "windsurf"]


def test_gui_flags_are_correct():
    by = {a.key: a for a in build_registry()}
    assert by["claude-desktop"].gui is True
    assert by["cursor"].gui is True
    assert by["windsurf"].gui is True
    assert by["gemini"].gui is False
    assert by["codex"].gui is False
    assert by["claude-code"].gui is False


def test_adapter_by_key_found_and_missing():
    assert adapter_by_key("cursor").label == "Cursor"
    assert adapter_by_key("nope") is None
