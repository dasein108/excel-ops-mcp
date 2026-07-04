from excel_mcp.installer import tui
from excel_mcp.installer.registry import build_registry


def _inputs(monkeypatch, seq):
    it = iter(seq)
    monkeypatch.setattr("builtins.input", lambda _="": next(it))


def test_checkbox_starts_unchecked_and_toggles(monkeypatch):
    adapters = build_registry()
    # toggle 1 and 3 on, then confirm
    _inputs(monkeypatch, ["1 3", ""])
    keys = tui._checkbox(adapters, set(), set(), "pick")
    assert keys == ["claude-desktop", "codex"]


def test_checkbox_default_selects_nothing(monkeypatch):
    adapters = build_registry()
    _inputs(monkeypatch, [""])  # confirm immediately
    assert tui._checkbox(adapters, set(), {"cursor", "codex"}, "pick") == []


def test_checkbox_all_then_toggle_off(monkeypatch):
    adapters = build_registry()
    _inputs(monkeypatch, ["a", "2", ""])  # all, then turn off #2 (claude-code)
    keys = tui._checkbox(adapters, set(), set(), "pick")
    assert "claude-code" not in keys
    assert len(keys) == len(adapters) - 1


def test_checkbox_none_clears(monkeypatch):
    adapters = build_registry()
    _inputs(monkeypatch, ["a", "n", ""])
    assert tui._checkbox(adapters, set(), set(), "pick") == []


def test_run_interactive_install_mode(monkeypatch):
    adapters = build_registry()
    _inputs(monkeypatch, ["1", "4", ""])  # mode=install, toggle #4 (gemini), confirm
    mode, keys = tui.run_interactive(adapters, set(), set())
    assert mode == "install"
    assert keys == ["gemini"]


def test_run_interactive_uninstall_only_lists_installed(monkeypatch):
    adapters = build_registry()
    # mode=2 (uninstall); installed={cursor}; candidates=[cursor]; toggle #1, confirm
    _inputs(monkeypatch, ["2", "1", ""])
    mode, keys = tui.run_interactive(adapters, set(), {"cursor"})
    assert mode == "uninstall"
    assert keys == ["cursor"]


def test_run_interactive_uninstall_nothing_installed(monkeypatch):
    adapters = build_registry()
    _inputs(monkeypatch, ["2"])  # mode=uninstall, no candidates → returns early
    mode, keys = tui.run_interactive(adapters, set(), set())
    assert mode == "uninstall"
    assert keys == []
