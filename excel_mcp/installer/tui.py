from __future__ import annotations

from .adapters.base import Adapter


def select_agents(adapters: list[Adapter], detected: set[str]) -> list[str]:
    """Interactively pick agents.

    Prefers the questionary checkbox UI, but falls back to a plain numbered
    prompt if the full-screen TUI cannot attach to the terminal (e.g. prompt
    toolkit's kqueue reader fails on some macOS / reattached-tty setups).
    """
    try:
        return _questionary_select(adapters, detected)
    except Exception:
        return _numbered_select(adapters, detected)


def _questionary_select(adapters: list[Adapter], detected: set[str]) -> list[str]:
    import questionary

    choices = [
        questionary.Choice(
            title=f"{a.label}" + ("  (detected)" if a.key in detected else "  (not found)"),
            value=a.key,
            checked=a.key in detected,
        )
        for a in adapters
    ]
    answer = questionary.checkbox(
        "Install excel-ops-mcp into which agents?", choices=choices
    ).ask()
    return answer or []


def _numbered_select(adapters: list[Adapter], detected: set[str]) -> list[str]:
    print("Install excel-ops-mcp into which agents?")
    for i, a in enumerate(adapters, 1):
        mark = "detected" if a.key in detected else "not found"
        print(f"  {i}) {a.label}  [{mark}]")
    default_keys = [a.key for a in adapters if a.key in detected]
    default_nums = ",".join(str(i) for i, a in enumerate(adapters, 1) if a.key in detected)
    prompt = f"Enter numbers (e.g. 1,4,6), 'all', or blank for detected [{default_nums}]: "
    try:
        raw = input(prompt).strip()
    except EOFError:
        raw = ""
    if not raw:
        return default_keys
    if raw.lower() == "all":
        return [a.key for a in adapters]
    keys: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(adapters):
            key = adapters[int(part) - 1].key
            if key not in keys:
                keys.append(key)
    return keys
