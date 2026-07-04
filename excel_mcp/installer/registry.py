from __future__ import annotations

import os
from pathlib import Path

from . import paths
from .adapters.base import Adapter
from .adapters.claude_code import ClaudeCodeCliAdapter
from .adapters.json_file import JsonDescriptor, JsonFileAdapter
from .adapters.toml_file import TomlDescriptor, TomlFileAdapter


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def build_registry() -> list[Adapter]:
    home = _home()
    claude_desktop = JsonFileAdapter(JsonDescriptor(
        key="claude-desktop", label="Claude Desktop", gui=True,
        path_fn=paths.claude_desktop_path,
        detect_dirs=(
            home / "Library" / "Application Support" / "Claude",
            home / ".config" / "Claude",
        ),
        restart_note="Fully quit and relaunch Claude Desktop.",
    ))
    codex = TomlFileAdapter(TomlDescriptor(
        key="codex", label="Codex",
        path_fn=paths.codex_path,
        detect_dirs=(home / ".codex",),
        cli_name="codex",
        restart_note="Restart Codex.",
    ))
    gemini = JsonFileAdapter(JsonDescriptor(
        key="gemini", label="Gemini CLI", gui=False,
        path_fn=paths.gemini_path,
        detect_dirs=(home / ".gemini",),
        cli_name="gemini",
        restart_note="Restart the Gemini CLI.",
    ))
    cursor = JsonFileAdapter(JsonDescriptor(
        key="cursor", label="Cursor", gui=True,
        path_fn=paths.cursor_path,
        detect_dirs=(home / ".cursor",),
        restart_note="Reload Cursor and enable the server in Settings → MCP.",
    ))
    windsurf = JsonFileAdapter(JsonDescriptor(
        key="windsurf", label="Windsurf", gui=True,
        path_fn=paths.windsurf_path,
        detect_dirs=(home / ".codeium" / "windsurf",),
        restart_note="Click Refresh in the Cascade MCP panel.",
    ))
    return [claude_desktop, ClaudeCodeCliAdapter(), codex, gemini, cursor, windsurf]


def adapter_by_key(key: str) -> Adapter | None:
    for adapter in build_registry():
        if adapter.key == key:
            return adapter
    return None
