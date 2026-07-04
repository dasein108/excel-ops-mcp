from __future__ import annotations

import os
import sys
from pathlib import Path


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _appdata() -> Path | None:
    value = os.environ.get("APPDATA")
    return Path(value) if value else None


def _plat(platform: str | None) -> str:
    return platform if platform is not None else sys.platform


def cursor_path(platform: str | None = None) -> Path:
    return _home() / ".cursor" / "mcp.json"


def windsurf_path(platform: str | None = None) -> Path:
    return _home() / ".codeium" / "windsurf" / "mcp_config.json"


def gemini_path(platform: str | None = None) -> Path:
    return _home() / ".gemini" / "settings.json"


def codex_path(platform: str | None = None) -> Path:
    return _home() / ".codex" / "config.toml"


def claude_desktop_path(platform: str | None = None) -> Path | None:
    system = _plat(platform)
    if system == "darwin":
        return _home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if system.startswith("win"):
        appdata = _appdata()
        if appdata is None:
            return None
        return appdata / "Claude" / "claude_desktop_config.json"
    return _home() / ".config" / "Claude" / "claude_desktop_config.json"
