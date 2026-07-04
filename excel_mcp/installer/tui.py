from __future__ import annotations

from .adapters.base import Adapter


def select_agents(adapters: list[Adapter], detected: set[str], installed: set[str]) -> list[str]:
    """Interactively pick the desired set of agents.

    A checkbox is pre-checked when excel-ops-mcp is *already installed* in that
    agent (so a fresh machine starts all-unchecked). The returned list is the
    desired end state: the caller installs newly-checked agents and uninstalls
    newly-unchecked ones.

    Prefers the questionary checkbox UI, falling back to a plain numbered prompt
    if the full-screen TUI cannot attach to the terminal.
    """
    try:
        return _questionary_select(adapters, detected, installed)
    except Exception:
        return _numbered_select(adapters, detected, installed)


def _label(a: Adapter, detected: set[str], installed: set[str]) -> str:
    if a.key in installed:
        tag = "installed"
    elif a.key in detected:
        tag = "detected"
    else:
        tag = "not found"
    return f"{a.label}  ({tag})"


def _questionary_select(adapters: list[Adapter], detected: set[str], installed: set[str]) -> list[str]:
    import questionary

    choices = [
        questionary.Choice(
            title=_label(a, detected, installed),
            value=a.key,
            checked=a.key in installed,
        )
        for a in adapters
    ]
    answer = questionary.checkbox(
        "Select agents to install excel-ops-mcp into (unselect to uninstall):",
        choices=choices,
    ).ask()
    if answer is None:  # Ctrl-C / no terminal
        return []
    return answer


def _numbered_select(adapters: list[Adapter], detected: set[str], installed: set[str]) -> list[str]:
    print("Select agents to install excel-ops-mcp into (unselect to uninstall):")
    for i, a in enumerate(adapters, 1):
        mark = "x" if a.key in installed else " "
        print(f"  [{mark}] {i}) {_label(a, detected, installed)}")
    checked = ",".join(str(i) for i, a in enumerate(adapters, 1) if a.key in installed)
    hint = checked if checked else "none"
    prompt = f"Enter numbers for the desired set (e.g. 1,4,6), 'all', 'none', or blank to keep [{hint}]: "
    try:
        raw = input(prompt).strip()
    except EOFError:
        raw = ""
    if not raw:
        return [a.key for a in adapters if a.key in installed]
    if raw.lower() == "all":
        return [a.key for a in adapters]
    if raw.lower() == "none":
        return []
    keys: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(adapters):
            key = adapters[int(part) - 1].key
            if key not in keys:
                keys.append(key)
    return keys
