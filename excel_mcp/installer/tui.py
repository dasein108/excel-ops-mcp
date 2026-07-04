from __future__ import annotations

from .adapters.base import Adapter

Mode = str  # "install" | "uninstall"


def _label(a: Adapter, detected: set[str], installed: set[str]) -> str:
    if a.key in installed:
        tag = "installed"
    elif a.key in detected:
        tag = "detected"
    else:
        tag = "not found"
    return f"{a.label}  ({tag})"


def _choose_mode() -> Mode:
    print("excel-ops-mcp installer")
    print("  1) Install into agents")
    print("  2) Uninstall from agents")
    try:
        raw = input("Choose [1]: ").strip()
    except EOFError:
        return "install"
    return "uninstall" if raw == "2" else "install"


def _checkbox(items: list[Adapter], detected: set[str], installed: set[str], title: str) -> list[str]:
    """A plain-text [ ]/[X] multi-select. Starts with nothing selected."""
    chosen: set[str] = set()
    while True:
        print("\n" + title)
        for i, a in enumerate(items, 1):
            mark = "X" if a.key in chosen else " "
            print(f"  [{mark}] {i}) {_label(a, detected, installed)}")
        try:
            raw = input("Toggle numbers (e.g. 1 3 5), 'a'=all, 'n'=none, Enter=confirm: ").strip().lower()
        except EOFError:
            break
        if raw == "":
            break
        if raw in ("a", "all"):
            chosen = {a.key for a in items}
            continue
        if raw in ("n", "none"):
            chosen = set()
            continue
        for tok in raw.replace(",", " ").split():
            if tok.isdigit() and 1 <= int(tok) <= len(items):
                key = items[int(tok) - 1].key
                chosen.discard(key) if key in chosen else chosen.add(key)
    return [a.key for a in items if a.key in chosen]  # stable registry order


def run_interactive(
    adapters: list[Adapter], detected: set[str], installed: set[str]
) -> tuple[Mode, list[str]]:
    """Ask install-vs-uninstall, then pick agents. Returns (mode, selected keys)."""
    mode = _choose_mode()
    if mode == "uninstall":
        candidates = [a for a in adapters if a.key in installed]
        if not candidates:
            print("excel-ops-mcp is not installed in any agent — nothing to uninstall.")
            return "uninstall", []
        keys = _checkbox(candidates, detected, installed,
                         "Select agents to UNINSTALL excel-ops-mcp from:")
        return "uninstall", keys
    keys = _checkbox(adapters, detected, installed,
                     "Select agents to INSTALL excel-ops-mcp into:")
    return "install", keys
