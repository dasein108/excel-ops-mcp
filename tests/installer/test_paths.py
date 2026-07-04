from excel_mcp.installer import paths


def test_cursor_path_under_home(fake_home):
    p = paths.cursor_path(platform="linux")
    assert p == fake_home / ".cursor" / "mcp.json"


def test_windsurf_path(fake_home):
    p = paths.windsurf_path(platform="darwin")
    assert p == fake_home / ".codeium" / "windsurf" / "mcp_config.json"


def test_codex_path(fake_home):
    assert paths.codex_path(platform="linux") == fake_home / ".codex" / "config.toml"


def test_gemini_path(fake_home):
    assert paths.gemini_path(platform="linux") == fake_home / ".gemini" / "settings.json"


def test_claude_desktop_mac(fake_home):
    p = paths.claude_desktop_path(platform="darwin")
    assert p == fake_home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_windows_uses_appdata(fake_home):
    p = paths.claude_desktop_path(platform="win32")
    assert p == fake_home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_linux_config_dir(fake_home):
    p = paths.claude_desktop_path(platform="linux")
    assert p == fake_home / ".config" / "Claude" / "claude_desktop_config.json"
