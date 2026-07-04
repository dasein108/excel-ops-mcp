from __future__ import annotations

from .adapters.base import Adapter


def select_agents(adapters: list[Adapter], detected: set[str]) -> list[str]:
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
