from excel_mcp.installer import tui
from excel_mcp.installer.registry import build_registry


def test_numbered_select_parses_numbers(monkeypatch):
    adapters = build_registry()
    monkeypatch.setattr("builtins.input", lambda _="": "1,5")
    keys = tui._numbered_select(adapters, set())
    assert keys == ["claude-desktop", "cursor"]


def test_numbered_select_all(monkeypatch):
    adapters = build_registry()
    monkeypatch.setattr("builtins.input", lambda _="": "all")
    keys = tui._numbered_select(adapters, set())
    assert keys == [a.key for a in adapters]


def test_numbered_select_blank_returns_detected(monkeypatch):
    adapters = build_registry()
    monkeypatch.setattr("builtins.input", lambda _="": "")
    keys = tui._numbered_select(adapters, {"codex", "cursor"})
    assert set(keys) == {"codex", "cursor"}


def test_numbered_select_ignores_out_of_range_and_dupes(monkeypatch):
    adapters = build_registry()
    monkeypatch.setattr("builtins.input", lambda _="": "1,1,99,abc,3")
    keys = tui._numbered_select(adapters, set())
    assert keys == ["claude-desktop", "codex"]


def test_select_agents_falls_back_when_questionary_raises(monkeypatch):
    adapters = build_registry()

    def boom(*a, **k):
        raise OSError("[Errno 22] Invalid argument")

    monkeypatch.setattr(tui, "_questionary_select", boom)
    monkeypatch.setattr("builtins.input", lambda _="": "2")
    keys = tui.select_agents(adapters, set())
    assert keys == ["claude-code"]
